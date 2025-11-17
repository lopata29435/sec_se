"""
Тесты для проверки валидации входных данных и обработки ошибок
P06: Тесты (включая негативные сценарии)
"""

from datetime import date, timedelta

import pytest


class TestInputValidation:
    """Тесты валидации входных данных"""

    def test_create_habit_valid(self, authenticated_client):
        """Позитивный тест: создание привычки с валидными данными"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "Morning Exercise",
                "description": "30 minutes of exercise",
                "frequency": "daily",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Morning Exercise"
        assert data["frequency"] == "daily"

    def test_create_habit_empty_name(self, authenticated_client):
        """Негативный тест: пустое имя привычки"""
        response = authenticated_client.post(
            "/habits", json={"name": "", "description": "Test", "frequency": "daily"}
        )
        assert response.status_code == 422
        data = response.json()
        assert data["type"] == "https://api.habittracker.dev/errors/validation"
        assert "correlation_id" in data

    def test_create_habit_name_too_long(self, authenticated_client):
        """Негативный тест: слишком длинное имя"""
        long_name = "A" * 101
        response = authenticated_client.post(
            "/habits",
            json={"name": long_name, "description": "Test", "frequency": "daily"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "validation" in data["type"].lower()

    def test_create_habit_xss_attempt(self, authenticated_client):
        """Негативный тест: попытка XSS атаки через имя"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "<script>alert('xss')</script>",
                "description": "Test",
                "frequency": "daily",
            },
        )
        assert response.status_code == 422
        data = response.json()
        # Проверяем что в массиве ошибок есть сообщение о недопустимом символе
        error_messages = " ".join(err["message"].lower() for err in data.get("errors", []))
        assert "недопустимый символ" in error_messages or "forbidden" in error_messages

    def test_create_habit_dangerous_chars_in_description(self, authenticated_client):
        """Негативный тест: опасные символы в описании"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "Test Habit",
                "description": "Test <img src=x onerror=alert(1)>",
                "frequency": "daily",
            },
        )
        assert response.status_code == 422

    def test_create_habit_invalid_frequency(self, authenticated_client):
        """Негативный тест: неправильное значение frequency"""
        response = authenticated_client.post(
            "/habits",
            json={"name": "Test", "description": "Test", "frequency": "hourly"},
        )
        assert response.status_code == 422

    def test_create_habit_negative_target_count(self, authenticated_client):
        """Негативный тест: отрицательное значение target_count"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "Test Habit",
                "description": "Test",
                "frequency": "daily",
                "target_count": -5,
            },
        )
        assert response.status_code == 422

    def test_create_habit_target_count_too_large(self, authenticated_client):
        """Негативный тест: слишком большое значение target_count"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "Test Habit",
                "description": "Test",
                "frequency": "daily",
                "target_count": 101,
            },
        )
        assert response.status_code == 422


class TestTrackingValidation:
    """Тесты валидации отслеживания привычек"""

    @pytest.fixture
    def habit_id(self, authenticated_client):
        """Создание тестовой привычки"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "Test Habit for Tracking",
                "description": "Test",
                "frequency": "daily",
            },
        )
        assert response.status_code == 201
        return response.json()["id"]

    def test_track_habit_future_date(self, authenticated_client, habit_id):
        """Негативный тест: дата в будущем"""
        future_date = (date.today() + timedelta(days=1)).isoformat()

        response = authenticated_client.post(
            f"/habits/{habit_id}/track",
            json={"habit_id": habit_id, "completed_date": future_date, "count": 1},
        )
        assert response.status_code == 422
        data = response.json()
        # Проверяем что в массиве ошибок есть сообщение о будущей дате
        error_messages = " ".join(err["message"].lower() for err in data.get("errors", []))
        assert "будущем" in error_messages or "future" in error_messages

    def test_track_habit_invalid_count(self, authenticated_client, habit_id):
        """Негативный тест: неправильное количество"""
        response = authenticated_client.post(
            f"/habits/{habit_id}/track",
            json={"habit_id": habit_id, "count": 0},
        )
        assert response.status_code == 422

    def test_track_habit_count_too_large(self, authenticated_client, habit_id):
        """Негативный тест: слишком большое количество"""
        response = authenticated_client.post(
            f"/habits/{habit_id}/track",
            json={"habit_id": habit_id, "count": 101},
        )
        assert response.status_code == 422

    def test_track_habit_xss_in_notes(self, authenticated_client, habit_id):
        """Негативный тест: XSS в заметках"""
        response = authenticated_client.post(
            f"/habits/{habit_id}/track",
            json={
                "habit_id": habit_id,
                "count": 1,
                "notes": "<script>alert('xss')</script>",
            },
        )
        assert response.status_code == 422

    def test_track_nonexistent_habit(self, authenticated_client):
        """Негативный тест: несуществующая привычка"""
        response = authenticated_client.post(
            "/habits/99999/track", json={"habit_id": 99999, "count": 1}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["type"] == "https://api.habittracker.dev/errors/not-found"
        assert "correlation_id" in data


class TestBoundaryValues:
    """Тесты граничных значений"""

    def test_habit_name_min_length(self, authenticated_client):
        """Граничное значение: имя минимальной длины"""
        response = authenticated_client.post(
            "/habits", json={"name": "A", "description": "", "frequency": "daily"}
        )
        assert response.status_code == 201

    def test_habit_name_max_length(self, authenticated_client):
        """Граничное значение: имя максимальной длины"""
        response = authenticated_client.post(
            "/habits",
            json={"name": "A" * 100, "description": "", "frequency": "daily"},
        )
        assert response.status_code == 201

    def test_habit_description_max_length(self, authenticated_client):
        """Граничное значение: описание максимальной длины"""
        response = authenticated_client.post(
            "/habits",
            json={"name": "Test", "description": "A" * 500, "frequency": "daily"},
        )
        assert response.status_code == 201

    def test_tracking_count_min(self, authenticated_client):
        """Граничное значение: минимальное количество"""
        # Сначала создать привычку
        habit_response = authenticated_client.post(
            "/habits", json={"name": "Test", "frequency": "daily"}
        )
        habit_id = habit_response.json()["id"]

        response = authenticated_client.post(
            f"/habits/{habit_id}/track", json={"habit_id": habit_id, "count": 1}
        )
        assert response.status_code == 201

    def test_tracking_count_max(self, authenticated_client):
        """Граничное значение: максимальное количество"""
        habit_response = authenticated_client.post(
            "/habits", json={"name": "Test", "frequency": "daily"}
        )
        habit_id = habit_response.json()["id"]

        response = authenticated_client.post(
            f"/habits/{habit_id}/track", json={"habit_id": habit_id, "count": 100}
        )
        assert response.status_code == 201
