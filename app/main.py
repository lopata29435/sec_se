from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

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

# Middleware безопасности (NFR-03, R02) - Отключено, раскомментировать для активации
# app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
# app.add_middleware(SecurityHeadersMiddleware)


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


_DB = {"items": []}


class FrequencyType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


_HABITS_DB = {
    "habits": [],
    "tracking_records": [],
    "next_habit_id": 1,
    "next_record_id": 1,
}


@app.post("/items")
def create_item(name: str):
    if not name or len(name) > 100:
        raise ApiError(
            code="validation_error", message="name must be 1..100 chars", status=422
        )
    item = {"id": len(_DB["items"]) + 1, "name": name}
    _DB["items"].append(item)
    return item


@app.get("/items/{item_id}")
def get_item(item_id: int):
    for it in _DB["items"]:
        if it["id"] == item_id:
            return it
    raise ApiError(code="not_found", message="item not found", status=404)


# Habit Tracker Endpoints


@app.post("/habits")
def create_habit(
    name: str, description: str = "", frequency: FrequencyType = FrequencyType.DAILY
):
    """Создать новую привычку для отслеживания"""
    if not name or len(name.strip()) == 0:
        raise ApiError(
            code="validation_error", message="Habit name cannot be empty", status=422
        )

    if len(name) > 100:
        raise ApiError(
            code="validation_error",
            message="Habit name must be less than 100 characters",
            status=422,
        )

    if len(description) > 500:
        raise ApiError(
            code="validation_error",
            message="Description must be less than 500 characters",
            status=422,
        )

    habit = {
        "id": _HABITS_DB["next_habit_id"],
        "name": name.strip(),
        "description": description.strip(),
        "frequency": frequency.value,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }

    _HABITS_DB["habits"].append(habit)
    _HABITS_DB["next_habit_id"] += 1

    return habit


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


@app.post("/habits/{habit_id}/track")
def track_habit(habit_id: int, completed_at: Optional[str] = None):
    """Отметить выполнение привычки на определенную дату"""
    habit = _find_habit_by_id(habit_id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    if not habit["is_active"]:
        raise ApiError(
            code="inactive_habit", message="Cannot track inactive habit", status=400
        )

    if completed_at:
        try:
            track_date = datetime.fromisoformat(
                completed_at.replace("Z", "+00:00")
            ).date()
        except ValueError:
            try:
                track_date = datetime.strptime(completed_at, "%Y-%m-%d").date()
            except ValueError:
                raise ApiError(
                    code="validation_error",
                    message="Invalid date format. Use YYYY-MM-DD or ISO format",
                    status=422,
                )
    else:
        track_date = date.today()

    existing_record = None
    for record in _HABITS_DB["tracking_records"]:
        if (
            record["habit_id"] == habit_id
            and record["completed_at"] == track_date.isoformat()
        ):
            existing_record = record
            break

    if existing_record:
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

    today = date.today()
    if period == "week":
        start_date = today - timedelta(days=7)
        expected_days = 7
    elif period == "month":
        start_date = today - timedelta(days=30)
        expected_days = 30
    else:
        start_date = today - timedelta(days=365)
        expected_days = 365

    period_records = []
    for record in habit_records:
        record_date = datetime.strptime(record["completed_at"], "%Y-%m-%d").date()
        if record_date >= start_date:
            period_records.append(record)

    completed_days = len(period_records)
    completion_rate = (completed_days / expected_days) * 100 if expected_days > 0 else 0

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

    longest_streak = 0
    temp_streak = 0

    if habit_records:
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
        "period_end": today.isoformat(),
    }


@app.put("/habits/{habit_id}")
def update_habit(habit_id: int, update_data: dict = Body(...)):
    """Обновить информацию о привычке или деактивировать её"""
    habit = _find_habit_by_id(habit_id)
    if not habit:
        raise ApiError(code="not_found", message="Habit not found", status=404)

    name = update_data.get("name")
    description = update_data.get("description")
    is_active = update_data.get("is_active")
    frequency = update_data.get("frequency")

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

    if description is not None and len(description) > 500:
        raise ApiError(
            code="validation_error",
            message="Description must be less than 500 characters",
            status=422,
        )

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
        if frequency in ["daily", "weekly", "monthly"]:
            habit["frequency"] = frequency
            updated_fields.append("frequency")
        else:
            raise ApiError(
                code="validation_error",
                message="Frequency must be one of: daily, weekly, monthly",
                status=422,
            )

    if not updated_fields:
        return {"message": "No fields to update", "habit": habit}

    habit["updated_at"] = datetime.now().isoformat()

    return {
        "message": f"Habit updated successfully. Updated fields: {', '.join(updated_fields)}",
        "habit": habit,
    }
