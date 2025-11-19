# tests/conftest.py
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ВАЖНО: Установить переменные окружения ДО импорта модулей приложения
os.environ["RATE_LIMIT_ENABLED"] = "false"  # Отключаем rate limiting для тестов
os.environ["USE_PERSISTENT_DB"] = "false"  # Используем in-memory DB для тестов
os.environ["DATABASE_URL"] = "sqlite:///./test.db"  # Локальная файловая SQLite для тестов

ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Инициализация схемы БД (создание таблиц) перед тестами
from app.database import Base, engine  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def test_client():
    """Создать тестовый клиент FastAPI"""
    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="function")
def test_user_credentials():
    """Тестовые учетные данные пользователя (уникальные для каждого теста)"""
    import time

    timestamp = str(int(time.time() * 1000000))  # микросекунды для уникальности
    return {
        "username": f"testuser_{timestamp}",
        "password": "TestPassword123!",
        "email": f"test_{timestamp}@example.com",
    }


@pytest.fixture(scope="function")
def authenticated_client(test_client, test_user_credentials):
    """Создать аутентифицированного клиента с JWT токеном"""
    # Регистрация тестового пользователя
    register_response = test_client.post(
        "/register",
        json={
            "username": test_user_credentials["username"],
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )

    # Если пользователь уже существует, это нормально
    if register_response.status_code not in [201, 400]:
        raise Exception(f"Registration failed: {register_response.json()}")

    # Логин для получения токена
    login_response = test_client.post(
        "/login",
        data={  # OAuth2 требует form data, не JSON
            "username": test_user_credentials["username"],
            "password": test_user_credentials["password"],
        },
    )

    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"

    token = login_response.json()["access_token"]

    # Создаем новый клиент с токеном в заголовках
    test_client.headers = {
        **test_client.headers,
        "Authorization": f"Bearer {token}",
    }

    yield test_client

    # Очистка: удаляем заголовок авторизации
    if "Authorization" in test_client.headers:
        del test_client.headers["Authorization"]
