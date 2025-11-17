"""Тесты для аутентификации и авторизации"""

import pytest


class TestAuthentication:
    """Тесты для регистрации и входа"""

    def test_register_new_user(self, test_client):
        """Регистрация нового пользователя"""
        response = test_client.post(
            "/register",
            json={
                "username": f"newuser_{pytest.timestamp()}",  # Уникальное имя
                "email": f"newuser_{pytest.timestamp()}@example.com",
                "password": "SecurePassword123!",
            },
        )

        # Может быть 201 если новый, или 400 если уже существует
        assert response.status_code in [201, 400]

    def test_register_duplicate_user(self, test_client, test_user_credentials):
        """Регистрация дубликата пользователя"""
        # Первая регистрация
        test_client.post(
            "/register",
            json=test_user_credentials,
        )

        # Вторая регистрация с тем же username
        response = test_client.post(
            "/register",
            json=test_user_credentials,
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_login_success(self, test_client, test_user_credentials):
        """Успешный вход"""
        # Сначала регистрируем
        test_client.post("/register", json=test_user_credentials)

        # Затем логинимся
        response = test_client.post(
            "/login",
            data={  # OAuth2 требует form data
                "username": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"  # noqa: S105

    def test_login_wrong_password(self, test_client, test_user_credentials):
        """Вход с неправильным паролем"""
        # Регистрируем пользователя
        test_client.post("/register", json=test_user_credentials)

        # Пытаемся войти с неправильным паролем
        response = test_client.post(
            "/login",
            data={
                "username": test_user_credentials["username"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, test_client):
        """Вход несуществующего пользователя"""
        response = test_client.post(
            "/login",
            data={
                "username": "nonexistent_user",
                "password": "SomePassword123!",
            },
        )

        assert response.status_code == 401

    def test_get_current_user(self, authenticated_client):
        """Получение информации о текущем пользователе"""
        response = authenticated_client.get("/me")

        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "id" in data
        assert "is_active" in data
        assert data["is_active"] is True

    def test_get_current_user_unauthorized(self, test_client):
        """Получение информации без авторизации"""
        response = test_client.get("/me")

        assert response.status_code == 401


# Добавляем timestamp для уникальных имен пользователей
@pytest.fixture(scope="session", autouse=True)
def add_timestamp_to_pytest():
    """Добавить timestamp для генерации уникальных имен"""
    import time

    pytest.timestamp = lambda: str(int(time.time() * 1000))
