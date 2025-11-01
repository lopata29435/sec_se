"""
Обработчики ошибок с поддержкой RFC 7807 Problem Details
P06: Ошибки в формате RFC 7807 (маскирование, correlation_id, карта ошибок)
"""

import uuid
from typing import Optional, Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import USE_RFC7807_ERRORS


class ApiError(Exception):
    """Базовое исключение API с поддержкой RFC 7807"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        status: Optional[int] = None,  # Обратная совместимость
        detail: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        self.code = code
        self.message = message
        # Поддержка обоих параметров для обратной совместимости
        self.status_code = status if status is not None else status_code
        self.status = self.status_code  # Алиас для старого кода
        self.detail = detail or message
        self.correlation_id = correlation_id or str(uuid.uuid4())
        super().__init__(self.message)


# Карта типов ошибок для RFC 7807
ERROR_TYPE_MAP = {
    "validation_error": {
        "type": "https://api.habittracker.dev/errors/validation",
        "title": "Validation Error",
        "description": "Входные данные не прошли валидацию",
    },
    "not_found": {
        "type": "https://api.habittracker.dev/errors/not-found",
        "title": "Resource Not Found",
        "description": "Запрошенный ресурс не найден",
    },
    "conflict": {
        "type": "https://api.habittracker.dev/errors/conflict",
        "title": "Resource Conflict",
        "description": "Конфликт при создании/обновлении ресурса",
    },
    "rate_limit": {
        "type": "https://api.habittracker.dev/errors/rate-limit",
        "title": "Rate Limit Exceeded",
        "description": "Превышен лимит запросов",
    },
    "internal_error": {
        "type": "https://api.habittracker.dev/errors/internal",
        "title": "Internal Server Error",
        "description": "Внутренняя ошибка сервера",
    },
    "unauthorized": {
        "type": "https://api.habittracker.dev/errors/unauthorized",
        "title": "Unauthorized",
        "description": "Требуется аутентификация",
    },
    "forbidden": {
        "type": "https://api.habittracker.dev/errors/forbidden",
        "title": "Forbidden",
        "description": "Недостаточно прав доступа",
    },
}


def create_error_response(
    request: Request,
    error_code: str,
    detail: str,
    status_code: int,
    correlation_id: Optional[str] = None,
    mask_sensitive: bool = True,
) -> JSONResponse:
    """
    Создание ответа об ошибке в формате RFC 7807

    Args:
        request: HTTP запрос
        error_code: Код ошибки из ERROR_TYPE_MAP
        detail: Детальное описание ошибки
        status_code: HTTP статус код
        correlation_id: ID для корреляции в логах
        mask_sensitive: Маскировать чувствительную информацию

    Returns:
        JSONResponse с телом в формате RFC 7807
    """
    correlation_id = correlation_id or str(uuid.uuid4())

    # Получение типа ошибки из карты
    error_info = ERROR_TYPE_MAP.get(
        error_code,
        {
            "type": "https://api.habittracker.dev/errors/unknown",
            "title": "Unknown Error",
            "description": "Неизвестная ошибка",
        },
    )

    # Маскирование чувствительной информации в production
    if mask_sensitive and status_code >= 500:
        detail = error_info["description"]  # Не раскрываем внутренние детали

    # Формирование ответа RFC 7807
    problem_detail = {
        "type": error_info["type"],
        "title": error_info["title"],
        "status": status_code,
        "detail": detail,
        "instance": str(request.url.path),
        "correlation_id": correlation_id,
    }

    return JSONResponse(status_code=status_code, content=problem_detail)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Обработчик кастомных ApiError с поддержкой обоих форматов"""

    if USE_RFC7807_ERRORS:
        # RFC 7807 формат
        return create_error_response(
            request=request,
            error_code=exc.code,
            detail=exc.detail,
            status_code=exc.status_code,
            correlation_id=exc.correlation_id,
            mask_sensitive=True,
        )
    else:
        # Старый формат для обратной совместимости
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )


async def validation_error_handler(
    request: Request, exc: Union[ValidationError, RequestValidationError]
) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic и FastAPI
    Поддерживает оба формата: RFC 7807 и старый формат
    """
    correlation_id = str(uuid.uuid4())

    if USE_RFC7807_ERRORS:
        # Формирование детального описания ошибок валидации (RFC 7807)
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({"field": field, "message": error["msg"], "type": error["type"]})

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "type": "https://api.habittracker.dev/errors/validation",
                "title": "Validation Error",
                "status": 422,
                "detail": "Request validation failed",
                "errors": errors,
                "correlation_id": correlation_id,
            },
        )
    else:
        # Старый формат для обратной совместимости
        # Берем первую ошибку для простоты
        first_error = exc.errors()[0]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_error",
                    "message": first_error["msg"],
                }
            },
        )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик неожиданных исключений

    Маскирует детали внутренних ошибок, логирует с correlation_id
    """
    correlation_id = str(uuid.uuid4())

    # В production НЕ раскрываем детали внутренних ошибок
    # В development можно показать больше информации
    import os

    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        detail = "Внутренняя ошибка сервера. Обратитесь к администратору."
    else:
        # В development показываем детали для отладки
        detail = f"Internal error: {type(exc).__name__}: {str(exc)}"

    # TODO: Добавить логирование с correlation_id
    # logger.error(
    #     f"Unhandled exception: {exc}",
    #     extra={"correlation_id": correlation_id, "path": request.url.path}
    # )

    return create_error_response(
        request=request,
        error_code="internal_error",
        detail=detail,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        correlation_id=correlation_id,
        mask_sensitive=True,
    )


def mask_pii_in_logs(data: str) -> str:
    """
    Маскирование PII (Personally Identifiable Information) в логах

    Заменяет email, телефоны, токены на ***

    Args:
        data: Строка для маскирования

    Returns:
        Строка с замаскированными данными
    """
    import re

    # Маскировать email
    data = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "***@***.***",
        data,
    )

    # Маскировать телефоны
    data = re.sub(r"\b\+?\d{10,15}\b", "***PHONE***", data)

    # Маскировать токены (JWT подобные строки)
    data = re.sub(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b", "***TOKEN***", data)

    # Маскировать API ключи
    data = re.sub(r"\b[A-Za-z0-9]{32,}\b", "***API_KEY***", data)

    return data
