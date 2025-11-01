"""
Модуль для экспорта метрик в формате Prometheus
Отслеживает количество запросов, время ответа, ошибки и другие метрики
"""

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

# Метрики запросов
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    ["method", "endpoint"],
)

# Метрики ошибок
http_errors_total = Counter(
    "http_errors_total",
    "Total number of HTTP errors",
    ["method", "endpoint", "status_code"],
)

# Метрики аутентификации
auth_requests_total = Counter(
    "auth_requests_total",
    "Total number of authentication requests",
    ["endpoint", "status"],
)

auth_failures_total = Counter(
    "auth_failures_total", "Total number of authentication failures", ["reason"]
)

# Метрики базы данных
db_connections_total = Gauge("db_connections_total", "Number of active database connections")

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds", "Database query duration in seconds", ["query_type"]
)

# Метрики бизнес-логики
habits_created_total = Counter("habits_created_total", "Total number of habits created")

habits_tracked_total = Counter(
    "habits_tracked_total", "Total number of habit tracking records created"
)

users_registered_total = Counter("users_registered_total", "Total number of users registered")


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматического сбора метрик HTTP запросов
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Игнорируем метрики для самого endpoint метрик
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Увеличиваем счетчик запросов в процессе
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Засекаем время начала запроса
        start_time = time.time()

        try:
            # Выполняем запрос
            response = await call_next(request)
            status_code = response.status_code

            # Записываем метрики
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()

            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

            # Отслеживаем ошибки (4xx и 5xx)
            if status_code >= 400:
                http_errors_total.labels(
                    method=method, endpoint=endpoint, status_code=status_code
                ).inc()

            return response

        finally:
            # Уменьшаем счетчик запросов в процессе
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def metrics_endpoint() -> Response:
    """
    Endpoint для экспорта метрик в формате Prometheus

    Returns:
        Response с метриками в формате Prometheus
    """
    from fastapi import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def track_auth_request(endpoint: str, success: bool):
    """
    Отслеживание запросов аутентификации

    Args:
        endpoint: Endpoint аутентификации (login, register)
        success: Успешность запроса
    """
    status = "success" if success else "failure"
    auth_requests_total.labels(endpoint=endpoint, status=status).inc()


def track_auth_failure(reason: str):
    """
    Отслеживание неудачных попыток аутентификации

    Args:
        reason: Причина неудачи (invalid_credentials, user_exists, etc.)
    """
    auth_failures_total.labels(reason=reason).inc()


def track_habit_created():
    """Отслеживание создания привычки"""
    habits_created_total.inc()


def track_habit_tracked():
    """Отслеживание записи выполнения привычки"""
    habits_tracked_total.inc()


def track_user_registered():
    """Отслеживание регистрации пользователя"""
    users_registered_total.inc()
