"""
Middleware безопасности для Habit Tracker API
Реализует контроли безопасности из модели угроз (docs/threat-model/)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для ограничения частоты запросов (защита от DoS атак)
    Связь с моделью угроз: R02, T1.4, T10.3
    NFR-03: Максимум 100 запросов/минуту на IP адрес

    Смягчаемые угрозы:
    - T1.4: DDoS flood запросами
    - T10.3: Флуд запросами отслеживания привычек
    - T8.3: Генерация массовых ошибок
    """

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[datetime]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Получить IP клиента (учитывать X-Forwarded-For в продакшене за прокси)
        client_ip = request.client.host if request.client else "unknown"

        # Специальная обработка для health check (повышенный лимит)
        if request.url.path == "/health":
            # Health check получает в 10 раз больший лимит (1000 запросов/мин)
            limit = self.requests_per_minute * 10
        else:
            limit = self.requests_per_minute

        # Очистка старых запросов (старше 1 минуты)
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] if req_time > cutoff
        ]

        # Проверка превышения лимита
        if len(self.requests[client_ip]) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": f"Превышен лимит запросов. Максимум {limit} запросов в минуту.",
                    }
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Записать текущий запрос
        self.requests[client_ip].append(now)

        # Добавить заголовки лимита в ответ
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(
            limit - len(self.requests[client_ip])
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Добавление заголовков безопасности ко всем ответам
    Смягчает:
    - T1.3: Утечка информации через заголовки
    - XSS, clickjacking, MIME sniffing атаки
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (HTTP Strict Transport Security) - NFR-06
        # Включать только в продакшене с HTTPS
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (базовая)
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


# Константы для квот ресурсов (R06, T5.3)
MAX_HABITS_PER_USER = 100  # Смягчает T5.3: DoS через неограниченное создание привычек
MAX_TRACKING_RECORDS_PER_HABIT = 10000  # Смягчает T15.3: Исчерпание памяти
MAX_REQUEST_SIZE_MB = 1  # Смягчает T3.2: DoS через большие payload


def validate_resource_quota(
    current_count: int, max_count: int, resource_type: str
) -> None:
    """
    Валидация лимитов квот ресурсов (R06)
    Raises:
        ApiError: Если квота превышена
    """
    from app.main import ApiError

    if current_count >= max_count:
        raise ApiError(
            code="quota_exceeded",
            message=f"Достигнут максимальный лимит {resource_type} ({max_count})",
            status=403,
        )
