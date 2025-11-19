"""
Модуль аудит-логирования для Habit Tracker API
Логирует все критичные операции (CREATE, UPDATE, DELETE) с user_id и correlation_id
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.config import AUDIT_LOG_ACTIONS, AUDIT_LOG_ENABLED

# Настройка логгера для аудита
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Формат логов: JSON для удобства парсинга
formatter = logging.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
)

# Хендлер для записи в файл (путь можно переопределить переменной окружения)
_audit_log_path = os.getenv("AUDIT_LOG_PATH", "audit.log")
_audit_dir = os.path.dirname(_audit_log_path)
if _audit_dir:
    os.makedirs(_audit_dir, exist_ok=True)
file_handler = logging.FileHandler(_audit_log_path)
file_handler.setFormatter(formatter)
audit_logger.addHandler(file_handler)

# Консольный хендлер для разработки
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
audit_logger.addHandler(console_handler)


def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: Optional[int],
    user_id: Optional[int],
    correlation_id: str,
    details: Optional[dict] = None,
    status: str = "success",
) -> None:
    """
    Логирование аудит-события

    Args:
        action: Тип действия (CREATE, UPDATE, DELETE, READ)
        resource_type: Тип ресурса (habit, tracking_record, user)
        resource_id: ID ресурса
        user_id: ID пользователя, выполнившего действие
        correlation_id: ID для корреляции запросов
        details: Дополнительные детали операции
        status: Статус операции (success, failure)
    """
    if not AUDIT_LOG_ENABLED:
        return

    # Логируем только настроенные действия
    if action not in AUDIT_LOG_ACTIONS:
        return

    audit_data = {
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "correlation_id": correlation_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if details:
        audit_data["details"] = details

    # Логируем в формате JSON
    audit_logger.info(json.dumps(audit_data))


def log_create(
    resource_type: str,
    resource_id: int,
    user_id: int,
    correlation_id: str,
    details: Optional[dict] = None,
) -> None:
    """Логирование создания ресурса"""
    log_audit_event(
        action="CREATE",
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        correlation_id=correlation_id,
        details=details,
        status="success",
    )


def log_update(
    resource_type: str,
    resource_id: int,
    user_id: int,
    correlation_id: str,
    details: Optional[dict] = None,
) -> None:
    """Логирование обновления ресурса"""
    log_audit_event(
        action="UPDATE",
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        correlation_id=correlation_id,
        details=details,
        status="success",
    )


def log_delete(
    resource_type: str,
    resource_id: int,
    user_id: int,
    correlation_id: str,
    details: Optional[dict] = None,
) -> None:
    """Логирование удаления ресурса"""
    log_audit_event(
        action="DELETE",
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        correlation_id=correlation_id,
        details=details,
        status="success",
    )


def log_failed_operation(
    action: str,
    resource_type: str,
    user_id: Optional[int],
    correlation_id: str,
    error: str,
) -> None:
    """Логирование неудачной операции"""
    log_audit_event(
        action=action,
        resource_type=resource_type,
        resource_id=None,
        user_id=user_id,
        correlation_id=correlation_id,
        details={"error": error},
        status="failure",
    )
