"""
Модели данных с валидацией для Habit Tracker API
P06: Валидация и нормализация ввода
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrequencyType(str, Enum):
    """Частота отслеживания привычки"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class HabitCreate(BaseModel):
    """Модель для создания новой привычки с валидацией"""

    model_config = ConfigDict(str_strip_whitespace=True)  # Убрал str_min_length=1

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название привычки (1-100 символов)",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Описание привычки (максимум 500 символов)",
    )
    frequency: FrequencyType = Field(
        default=FrequencyType.DAILY, description="Частота выполнения привычки"
    )
    target_count: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Целевое количество выполнений (1-100)",
    )

    @field_validator("name")
    @classmethod
    def validate_name_content(cls, v: str) -> str:
        """Проверка содержимого имени (запрет опасных символов)"""
        # Pydantic уже проверил min_length=1, поэтому здесь только проверяем символы

        # Запрет потенциально опасных символов для XSS
        dangerous_chars = ["<", ">", "&", '"', "'", "`"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Название содержит недопустимый символ: {char}")

        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description_content(cls, v: str) -> str:
        """Проверка описания"""
        if not v:
            return ""

        # Запрет опасных символов в описании
        dangerous_chars = ["<", ">", "&", '"', "'", "`"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Описание содержит недопустимый символ: {char}")

        return v.strip()


class HabitResponse(BaseModel):
    """Модель ответа с информацией о привычке"""

    id: int
    name: str
    description: str
    frequency: str
    is_active: bool
    created_at: datetime
    target_count: Optional[int] = None


class HabitUpdate(BaseModel):
    """Модель для обновления привычки"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    frequency: Optional[FrequencyType] = None
    is_active: Optional[bool] = None
    target_count: Optional[int] = Field(None, ge=1, le=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Название не может быть пустым")

        dangerous_chars = ["<", ">", "&", '"', "'", "`"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Название содержит недопустимый символ: {char}")
        return v


class TrackingCreate(BaseModel):
    """Модель для отслеживания выполнения привычки"""

    model_config = ConfigDict(str_strip_whitespace=True)

    habit_id: int = Field(..., ge=1, description="ID привычки")
    completed_date: date = Field(
        default_factory=date.today, description="Дата выполнения (UTC)"
    )
    count: int = Field(default=1, ge=1, le=100, description="Количество выполнений")
    notes: str = Field(
        default="", max_length=200, description="Заметки (максимум 200 символов)"
    )

    @field_validator("completed_date")
    @classmethod
    def validate_date_not_future(cls, v: date) -> date:
        """Проверка, что дата не в будущем"""
        if v > date.today():
            raise ValueError("Дата выполнения не может быть в будущем")
        return v

    @field_validator("notes")
    @classmethod
    def validate_notes_content(cls, v: str) -> str:
        """Валидация заметок"""
        if not v:
            return ""

        dangerous_chars = ["<", ">", "&", '"', "'", "`"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Заметки содержат недопустимый символ: {char}")
        return v.strip()


class TrackingResponse(BaseModel):
    """Модель ответа для записи отслеживания"""

    id: int
    habit_id: int
    completed_date: date
    count: int
    notes: str
    created_at: datetime


class ItemCreate(BaseModel):
    """Модель для создания элемента (учебный пример)"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Название не может быть пустым")

        # Защита от XSS
        dangerous_chars = ["<", ">", "&", '"', "'", "`"]
        for char in dangerous_chars:
            if char in v:
                raise ValueError(f"Название содержит недопустимый символ: {char}")
        return v.strip()


class ItemResponse(BaseModel):
    """Модель ответа с информацией об элементе"""

    id: int
    name: str


class ErrorDetail(BaseModel):
    """Детали ошибки (RFC 7807 Problem Details)"""

    type: str = Field(..., description="URI идентификатор типа проблемы")
    title: str = Field(..., description="Краткое описание проблемы")
    status: int = Field(..., description="HTTP статус код")
    detail: str = Field(..., description="Детальное объяснение проблемы")
    instance: str = Field(
        ..., description="URI идентифицирующий конкретный случай проблемы"
    )
    correlation_id: Optional[str] = Field(None, description="ID для корреляции в логах")


class HealthResponse(BaseModel):
    """Ответ health-check endpoint"""

    status: str
    timestamp: datetime
    version: str = "0.1.0"
