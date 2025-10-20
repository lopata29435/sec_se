from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import Body, FastAPI, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

# Импорт обработчиков ошибок RFC 7807
from app.errors import (
    ApiError,
    api_error_handler,
    generic_exception_handler,
    validation_error_handler,
)

# Импорт моделей с валидацией
from app.models import HabitCreate, ItemCreate, ItemResponse, TrackingCreate

# Middleware безопасности из контролей модели угроз
# Раскомментировать для активации (сейчас отключено для совместимости)
# from app.security import RateLimitMiddleware, SecurityHeadersMiddleware,
#     MAX_HABITS_PER_USER, validate_resource_quota

app = FastAPI(
    title="Habit Tracker API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Регистрация обработчиков ошибок (RFC 7807)
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(
    RequestValidationError, validation_error_handler
)  # FastAPI validation
app.add_exception_handler(
    ValidationError, validation_error_handler
)  # Pydantic validation
app.add_exception_handler(Exception, generic_exception_handler)

# Middleware безопасности (NFR-03, R02) - Отключено, раскомментировать для активации
# app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
# app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


_DB = {"items": []}


_HABITS_DB = {
    "habits": [],
    "tracking_records": [],
    "next_habit_id": 1,
    "next_record_id": 1,
}


# === Items Endpoints (учебный пример) ===


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


# === Habit Tracker Endpoints ===


@app.post("/habits", status_code=201)
def create_habit(
    habit: HabitCreate = None,
    name: str = None,
    description: str = "",
    frequency: str = "daily",
):
    """
    Создать новую привычку для отслеживания
    Поддерживает два формата:
    1. JSON body с Pydantic валидацией (новый)
    2. Query параметры (старый, для обратной совместимости)
    """
    # Если переданы query параметры (старый формат)
    if habit is None and name is not None:
        # Создаем объект Pydantic из query параметров
        try:
            habit = HabitCreate(name=name, description=description, frequency=frequency)
        except Exception as e:
            # Если валидация провалилась, возвращаем ошибку
            raise ApiError(
                code="validation_error",
                message=str(e),
                status=422,
            ) from e
    elif habit is None:
        raise ApiError(
            code="validation_error",
            message="Either provide JSON body or name parameter",
            status=422,
        )

    # Проверка квоты (если активирована)
    # validate_resource_quota(len(_HABITS_DB["habits"]), MAX_HABITS_PER_USER, "habits")

    new_habit = {
        "id": _HABITS_DB["next_habit_id"],
        "name": habit.name,
        "description": habit.description,
        "frequency": (
            habit.frequency.value
            if hasattr(habit.frequency, "value")
            else habit.frequency
        ),
        "is_active": True,
        "created_at": datetime.now(),
        "target_count": habit.target_count,
    }

    _HABITS_DB["habits"].append(new_habit)
    _HABITS_DB["next_habit_id"] += 1

    return new_habit


@app.get("/habits")
def get_habits(active_only: bool = True):
    """Получить список всех привычек пользователя"""
    habits = _HABITS_DB["habits"]

    if active_only:
        habits = [h for h in habits if h["is_active"]]

    return {"habits": habits, "total": len(habits)}


def _find_habit_by_id(habit_id: int):
    """Вспомогательная функция для поиска привычки по ID"""
    for habit in _HABITS_DB["habits"]:
        if habit["id"] == habit_id:
            return habit
    return None


@app.post("/habits/{habit_id}/track", status_code=201)
def track_habit(
    habit_id: int,
    response: Response,
    tracking: TrackingCreate = None,
    completed_at: Optional[str] = None,
    count: int = 1,
    notes: str = "",
):
    """
    Отметить выполнение привычки
    Поддерживает два формата:
    1. JSON body с Pydantic валидацией (новый)
    2. Query параметры (старый, для обратной совместимости)
    """
    habit = _find_habit_by_id(habit_id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    if not habit["is_active"]:
        raise ApiError(
            code="inactive_habit", message="Cannot track inactive habit", status=400
        )

    # Если переданы query параметры (старый формат)
    if tracking is None:
        try:
            # Парсим дату если передана
            if completed_at:
                try:
                    track_date = datetime.fromisoformat(
                        completed_at.replace("Z", "+00:00")
                    ).date()
                except ValueError:
                    track_date = datetime.strptime(completed_at, "%Y-%m-%d").date()
            else:
                track_date = date.today()

            # Создаем объект Pydantic для валидации
            tracking = TrackingCreate(
                habit_id=habit_id,
                completed_date=track_date,
                count=count,
                notes=notes,
            )
        except Exception as e:
            raise ApiError(
                code="validation_error",
                message=str(e),
                status=422,
            ) from e

    # Используем данные из Pydantic модели
    track_date = tracking.completed_date

    existing_record = None
    for record in _HABITS_DB["tracking_records"]:
        if (
            record["habit_id"] == habit_id
            and record["completed_at"] == track_date.isoformat()
        ):
            existing_record = record
            break

    if existing_record:
        response.status_code = 200  # Для дубликатов возвращаем 200 вместо 201
        return {
            "message": "Habit already tracked for this date",
            "record": existing_record,
        }

    tracking_record = {
        "id": _HABITS_DB["next_record_id"],
        "habit_id": habit_id,
        "completed_at": track_date.isoformat(),
        "tracked_at": datetime.now().isoformat(),
    }

    _HABITS_DB["tracking_records"].append(tracking_record)
    _HABITS_DB["next_record_id"] += 1

    return {"message": "Habit tracked successfully", "record": tracking_record}


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
def get_habit_stats(habit_id: int, period: str = "month"):
    """Получить статистику выполнения привычки"""
    habit = _find_habit_by_id(habit_id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    if period not in ["week", "month", "year"]:
        raise ApiError(
            code="validation_error",
            message="Period must be one of: week, month, year",
            status=422,
        )

    habit_records = [
        r for r in _HABITS_DB["tracking_records"] if r["habit_id"] == habit_id
    ]

    start_date, expected_days = _calculate_period_dates(period)

    period_records = []
    for record in habit_records:
        record_date = datetime.strptime(record["completed_at"], "%Y-%m-%d").date()
        if record_date >= start_date:
            period_records.append(record)

    completed_days = len(period_records)
    completion_rate = (completed_days / expected_days) * 100 if expected_days > 0 else 0

    current_streak = _calculate_current_streak(habit_records)
    longest_streak = _calculate_longest_streak(habit_records)

    return {
        "habit_id": habit_id,
        "habit_name": habit["name"],
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
def update_habit(habit_id: int, update_data: dict | None = None):
    """Обновить информацию о привычке или деактивировать её"""
    if update_data is None:
        update_data = Body(...)

    habit = _find_habit_by_id(habit_id)
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
        habit["name"] = name.strip()
        updated_fields.append("name")

    if description is not None:
        habit["description"] = description.strip()
        updated_fields.append("description")

    if is_active is not None:
        habit["is_active"] = is_active
        updated_fields.append("is_active")

    if frequency is not None:
        habit["frequency"] = frequency
        updated_fields.append("frequency")

    if not updated_fields:
        return {"message": "No fields to update", "habit": habit}

    habit["updated_at"] = datetime.now().isoformat()

    return {
        "message": f"Habit updated successfully. Updated fields: {', '.join(updated_fields)}",
        "habit": habit,
    }
