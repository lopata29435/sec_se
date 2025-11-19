import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.orm import Session

# Аудит-логирование
from app.audit import log_create, log_update

# Аутентификация и авторизация
from app.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_active_user,
    get_user_by_username,
)
from app.config import AUDIT_LOG_ENABLED, AUTH_ENABLED, RATE_LIMIT_ENABLED

# База данных
from app.database import get_db

# Импорт обработчиков ошибок RFC 7807
from app.errors import (
    ApiError,
    api_error_handler,
    generic_exception_handler,
    validation_error_handler,
)

# Prometheus метрики
from app.metrics import (
    PrometheusMiddleware,
    metrics_endpoint,
    track_auth_failure,
    track_auth_request,
    track_habit_created,
    track_habit_tracked,
    track_user_registered,
)

# Импорт моделей с валидацией
from app.models import (
    Habit,
    HabitCreate,
    ItemCreate,
    ItemResponse,
    TrackingCreate,
    TrackingRecord,
    User,
    UserCreate,
    UserResponse,
)

# Middleware безопасности из контролей модели угроз
from app.security import (
    MAX_HABITS_PER_USER,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    validate_resource_quota,
)

app = FastAPI(
    title="Habit Tracker API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Регистрация обработчиков ошибок (RFC 7807)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)  # FastAPI validation
app.add_exception_handler(ValidationError, validation_error_handler)  # Pydantic validation
app.add_exception_handler(Exception, generic_exception_handler)

# Middleware безопасности (NFR-03, R02)
if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PrometheusMiddleware)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint
    Экспортирует метрики в формате Prometheus
    """
    return metrics_endpoint()


# === Authentication Endpoints ===


@app.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):  # noqa: B008
    """
    Регистрация нового пользователя

    Args:
        user_data: Данные пользователя (username, password)
        db: Сессия базы данных

    Returns:
        Созданный пользователь
    """
    # Проверка, существует ли пользователь
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        track_auth_failure("user_exists")
        track_auth_request("register", False)
        raise ApiError(
            code="user_exists",
            message="User with this username already exists",
            status=400,
        )

    # Создание пользователя
    user = create_user(db, user_data.username, user_data.password)

    # Отслеживание метрик
    track_user_registered()
    track_auth_request("register", True)

    # Логирование создания пользователя
    if AUDIT_LOG_ENABLED:
        log_create(
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
            correlation_id=str(uuid.uuid4()),
            details={"username": user.username},
        )

    return UserResponse(id=user.id, username=user.username, is_active=user.is_active)


@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """
    Вход пользователя и получение JWT токена

    Args:
        form_data: Форма с username и password
        db: Сессия базы данных

    Returns:
        Access token и тип токена
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        track_auth_failure("invalid_credentials")
        track_auth_request("login", False)
        raise ApiError(
            code="invalid_credentials",
            message="Incorrect username or password",
            status=401,
        )

    # Отслеживание успешного логина
    track_auth_request("login", True)

    # Создание JWT токена
    access_token = create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
):
    """
    Получить информацию о текущем пользователе

    Args:
        current_user: Текущий аутентифицированный пользователь

    Returns:
        Информация о пользователе
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
    )


_DB = {"items": []}

# === Items Endpoints (учебный пример - оставлен для обратной совместимости) ===


@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    """Создать новый элемент (учебный endpoint)"""
    new_item = {"id": len(_DB["items"]) + 1, "name": item.name}
    _DB["items"].append(new_item)
    return ItemResponse(**new_item)


@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    """Получить элемент по ID"""
    for it in _DB["items"]:
        if it["id"] == item_id:
            return ItemResponse(**it)
    raise ApiError(
        code="not_found",
        message=f"Элемент с ID {item_id} не найден",
        status_code=404,
    )


# === Habit Tracker Endpoints (с авторизацией и БД) ===


@app.post("/habits", status_code=201)
def create_habit(
    habit: HabitCreate,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: Optional[User] = (Depends(get_current_active_user)),  # noqa: B008
):
    """
    Создать новую привычку для отслеживания

    Args:
        habit: Данные привычки
        db: Сессия базы данных
        current_user: Текущий пользователь (если аутентификация включена)

    Returns:
        Созданная привычка
    """
    # Если аутентификация отключена, используем тестового пользователя
    if not AUTH_ENABLED:
        # Создаем или получаем тестового пользователя
        test_user = get_user_by_username(db, "test_user")
        if not test_user:
            test_user = create_user(db, "test_user", "test_password")
        current_user = test_user

    # Проверка квоты привычек
    user_habits_count = db.query(Habit).filter(Habit.owner_id == current_user.id).count()
    validate_resource_quota(user_habits_count, MAX_HABITS_PER_USER, "habits")

    # Создание привычки
    new_habit = Habit(
        name=habit.name,
        description=habit.description,
        frequency=(habit.frequency.value if hasattr(habit.frequency, "value") else habit.frequency),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        target_count=habit.target_count,
        owner_id=current_user.id,
    )

    db.add(new_habit)
    db.commit()
    db.refresh(new_habit)

    # Отслеживание метрик
    track_habit_created()

    # Логирование создания
    if AUDIT_LOG_ENABLED:
        log_create(
            resource_type="habit",
            resource_id=new_habit.id,
            user_id=current_user.id,
            correlation_id=str(uuid.uuid4()),
            details={"name": new_habit.name, "frequency": new_habit.frequency},
        )

    return {
        "id": new_habit.id,
        "name": new_habit.name,
        "description": new_habit.description,
        "frequency": new_habit.frequency,
        "is_active": new_habit.is_active,
        "created_at": new_habit.created_at,
        "target_count": new_habit.target_count,
    }


@app.get("/habits")
def get_habits(
    active_only: bool = True,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: Optional[User] = (Depends(get_current_active_user)),  # noqa: B008
):
    """
    Получить список всех привычек пользователя

    Args:
        active_only: Возвращать только активные привычки
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Список привычек пользователя
    """
    # Если аутентификация отключена, используем тестового пользователя
    if not AUTH_ENABLED:
        test_user = get_user_by_username(db, "test_user")
        if not test_user:
            test_user = create_user(db, "test_user", "test_password")
        current_user = test_user

    # Получение привычек пользователя
    query = db.query(Habit).filter(Habit.owner_id == current_user.id)

    if active_only:
        query = query.filter(Habit.is_active.is_(True))

    habits = query.all()

    habits_list = [
        {
            "id": h.id,
            "name": h.name,
            "description": h.description,
            "frequency": h.frequency,
            "is_active": h.is_active,
            "created_at": h.created_at,
            "target_count": h.target_count,
        }
        for h in habits
    ]

    return {"habits": habits_list, "total": len(habits_list)}


def _find_habit_by_id(db: Session, habit_id: int, user_id: int):
    """Вспомогательная функция для поиска привычки по ID и проверки владельца"""
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.owner_id == user_id).first()
    return habit


@app.post("/habits/{habit_id}/track", status_code=201)
def track_habit(
    habit_id: int,
    tracking: TrackingCreate,
    response: Response,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: Optional[User] = (Depends(get_current_active_user)),  # noqa: B008
):
    """
    Отметить выполнение привычки

    Args:
        habit_id: ID привычки
        tracking: Данные отслеживания
        response: Объект ответа FastAPI
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Результат отслеживания
    """
    # Если аутентификация отключена, используем тестового пользователя
    if not AUTH_ENABLED:
        test_user = get_user_by_username(db, "test_user")
        if not test_user:
            test_user = create_user(db, "test_user", "test_password")
        current_user = test_user

    # Проверка существования привычки и прав доступа
    habit = _find_habit_by_id(db, habit_id, current_user.id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    if not habit.is_active:
        raise ApiError(code="inactive_habit", message="Cannot track inactive habit", status=400)

    # Проверка дубликата
    existing_record = (
        db.query(TrackingRecord)
        .filter(
            TrackingRecord.habit_id == habit_id,
            TrackingRecord.completed_date == tracking.completed_date,
        )
        .first()
    )

    if existing_record:
        response.status_code = 200
        return {
            "message": "Habit already tracked for this date",
            "record": {
                "id": existing_record.id,
                "habit_id": existing_record.habit_id,
                "completed_date": existing_record.completed_date,
                "count": existing_record.count,
                "notes": existing_record.notes,
                "tracked_at": existing_record.tracked_at,
            },
        }

    # Создание записи отслеживания
    tracking_record = TrackingRecord(
        habit_id=habit_id,
        completed_date=tracking.completed_date,
        count=tracking.count,
        notes=tracking.notes,
        tracked_at=datetime.now(timezone.utc),
    )

    db.add(tracking_record)
    db.commit()
    db.refresh(tracking_record)

    # Отслеживание метрик
    track_habit_tracked()

    # Логирование
    if AUDIT_LOG_ENABLED:
        log_create(
            resource_type="tracking_record",
            resource_id=tracking_record.id,
            user_id=current_user.id,
            correlation_id=str(uuid.uuid4()),
            details={"habit_id": habit_id, "date": str(tracking.completed_date)},
        )

    return {
        "message": "Habit tracked successfully",
        "record": {
            "id": tracking_record.id,
            "habit_id": tracking_record.habit_id,
            "completed_date": tracking_record.completed_date,
            "count": tracking_record.count,
            "notes": tracking_record.notes,
            "tracked_at": tracking_record.tracked_at,
        },
    }


def _calculate_period_dates(period: str) -> tuple[date, int]:
    """Вычислить начальную дату и количество дней для периода."""
    today = date.today()
    if period == "week":
        return today - timedelta(days=7), 7
    elif period == "month":
        return today - timedelta(days=30), 30
    else:  # year
        return today - timedelta(days=365), 365


def _calculate_current_streak(habit_records: list[dict]) -> int:
    """Вычислить текущую серию выполнения привычки."""
    if not habit_records:
        return 0

    today = date.today()
    current_streak = 0
    check_date = today

    sorted_records = sorted(
        habit_records,
        key=lambda x: datetime.strptime(x["completed_at"], "%Y-%m-%d").date(),
        reverse=True,
    )

    for record in sorted_records:
        record_date = datetime.strptime(record["completed_at"], "%Y-%m-%d").date()
        if record_date == check_date:
            current_streak += 1
            check_date -= timedelta(days=1)
        elif record_date < check_date:
            break

    return current_streak


def _calculate_longest_streak(habit_records: list[dict]) -> int:
    """Вычислить самую длинную серию выполнения привычки."""
    if not habit_records:
        return 0

    longest_streak = 0
    temp_streak = 0

    sorted_asc = sorted(
        habit_records,
        key=lambda x: datetime.strptime(x["completed_at"], "%Y-%m-%d").date(),
    )

    prev_date = None
    for record in sorted_asc:
        record_date = datetime.strptime(record["completed_at"], "%Y-%m-%d").date()

        if prev_date is None or record_date == prev_date + timedelta(days=1):
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1

        prev_date = record_date

    return longest_streak


@app.get("/habits/{habit_id}/stats")
def get_habit_stats(
    habit_id: int,
    period: str = "month",
    db: Session = Depends(get_db),  # noqa: B008
    current_user: Optional[User] = (Depends(get_current_active_user)),  # noqa: B008
):
    """
    Получить статистику выполнения привычки

    Args:
        habit_id: ID привычки
        period: Период для статистики (week, month, year)
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Статистика привычки
    """
    # Если аутентификация отключена, используем тестового пользователя
    if not AUTH_ENABLED:
        test_user = get_user_by_username(db, "test_user")
        if not test_user:
            test_user = create_user(db, "test_user", "test_password")
        current_user = test_user

    # Проверка существования привычки и прав доступа
    habit = _find_habit_by_id(db, habit_id, current_user.id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    if period not in ["week", "month", "year"]:
        raise ApiError(
            code="validation_error",
            message="Period must be one of: week, month, year",
            status=422,
        )

    # Получение всех записей отслеживания
    habit_records = db.query(TrackingRecord).filter(TrackingRecord.habit_id == habit_id).all()

    start_date, expected_days = _calculate_period_dates(period)

    # Фильтрация по периоду
    period_records = [r for r in habit_records if r.completed_date >= start_date]

    completed_days = len(period_records)
    completion_rate = (completed_days / expected_days) * 100 if expected_days > 0 else 0

    # Преобразование SQLAlchemy моделей в словари для функций подсчета
    records_dicts = [{"completed_at": r.completed_date.isoformat()} for r in habit_records]

    current_streak = _calculate_current_streak(records_dicts)
    longest_streak = _calculate_longest_streak(records_dicts)

    return {
        "habit_id": habit_id,
        "habit_name": habit.name,
        "period": period,
        "stats": {
            "completed_days": completed_days,
            "expected_days": expected_days,
            "completion_rate": round(completion_rate, 2),
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "total_completions": len(habit_records),
        },
        "period_start": start_date.isoformat(),
        "period_end": date.today().isoformat(),
    }


def _validate_habit_name(name: str | None) -> None:
    """Валидация имени привычки."""
    if name is not None:
        if not name or len(name.strip()) == 0:
            raise ApiError(
                code="validation_error",
                message="Habit name cannot be empty",
                status=422,
            )
        if len(name) > 100:
            raise ApiError(
                code="validation_error",
                message="Habit name must be less than 100 characters",
                status=422,
            )


def _validate_description(description: str | None) -> None:
    """Валидация описания привычки."""
    if description is not None and len(description) > 500:
        raise ApiError(
            code="validation_error",
            message="Description must be less than 500 characters",
            status=422,
        )


def _validate_frequency(frequency: str | None) -> None:
    """Валидация частоты выполнения."""
    if frequency is not None and frequency not in ["daily", "weekly", "monthly"]:
        raise ApiError(
            code="validation_error",
            message="Frequency must be one of: daily, weekly, monthly",
            status=422,
        )


@app.put("/habits/{habit_id}")
def update_habit(
    habit_id: int,
    update_data: dict,
    db: Session = Depends(get_db),  # noqa: B008
    current_user: Optional[User] = (Depends(get_current_active_user)),  # noqa: B008
):
    """
    Обновить информацию о привычке или деактивировать её

    Args:
        habit_id: ID привычки
        update_data: Данные для обновления
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Обновленная привычка
    """
    # Если аутентификация отключена, используем тестового пользователя
    if not AUTH_ENABLED:
        test_user = get_user_by_username(db, "test_user")
        if not test_user:
            test_user = create_user(db, "test_user", "test_password")
        current_user = test_user

    # Проверка существования привычки и прав доступа
    habit = _find_habit_by_id(db, habit_id, current_user.id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    name = update_data.get("name")
    description = update_data.get("description")
    is_active = update_data.get("is_active")
    frequency = update_data.get("frequency")

    # Валидация
    _validate_habit_name(name)
    _validate_description(description)
    _validate_frequency(frequency)

    updated_fields = []

    if name is not None:
        habit.name = name.strip()
        updated_fields.append("name")

    if description is not None:
        habit.description = description.strip()
        updated_fields.append("description")

    if is_active is not None:
        habit.is_active = is_active
        updated_fields.append("is_active")

    if frequency is not None:
        habit.frequency = frequency
        updated_fields.append("frequency")

    if not updated_fields:
        return {
            "message": "No fields to update",
            "habit": {
                "id": habit.id,
                "name": habit.name,
                "description": habit.description,
                "frequency": habit.frequency,
                "is_active": habit.is_active,
                "created_at": habit.created_at,
                "target_count": habit.target_count,
            },
        }

    db.commit()
    db.refresh(habit)

    # Логирование обновления
    if AUDIT_LOG_ENABLED:
        log_update(
            resource_type="habit",
            resource_id=habit.id,
            user_id=current_user.id,
            correlation_id=str(uuid.uuid4()),
            details={"updated_fields": updated_fields},
        )

    return {
        "message": f"Habit updated successfully. Updated fields: {', '.join(updated_fields)}",
        "habit": {
            "id": habit.id,
            "name": habit.name,
            "description": habit.description,
            "frequency": habit.frequency,
            "is_active": habit.is_active,
            "created_at": habit.created_at,
            "target_count": habit.target_count,
        },
    }
