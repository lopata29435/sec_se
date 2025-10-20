"""
Тесты для проверки валидации входных данных и обработки ошибок
P06: Тесты (включая негативные сценарии)
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestInputValidation:
    """Тесты валидации входных данных"""

    def test_create_habit_valid(self):
        """Позитивный тест: создание привычки с валидными данными"""
        response = client.post(
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

    def test_create_habit_empty_name(self):
        """Негативный тест: пустое имя привычки"""
        response = client.post(
            "/habits", json={"name": "", "description": "Test", "frequency": "daily"}
        )
        assert response.status_code == 422
        data = response.json()
        assert data["type"] == "https://api.habittracker.dev/errors/validation"
        assert "correlation_id" in data

    def test_create_habit_name_too_long(self):
        """Негативный тест: слишком длинное имя"""
        long_name = "A" * 101
        response = client.post(
            "/habits",
            json={"name": long_name, "description": "Test", "frequency": "daily"},
        )
        assert response.status_code == 422
        data = response.json()
        assert "validation" in data["type"].lower()

    def test_create_habit_xss_attempt(self):
        """Негативный тест: попытка XSS атаки через имя"""
        response = client.post(
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
        error_messages = " ".join(
            err["message"].lower() for err in data.get("errors", [])
        )
        assert "недопустимый символ" in error_messages or "forbidden" in error_messages

    def test_create_habit_dangerous_chars_in_description(self):
        """Негативный тест: опасные символы в описании"""
        response = client.post(
            "/habits",
            json={
                "name": "Test Habit",
                "description": "Test <img src=x onerror=alert(1)>",
                "frequency": "daily",
            },
        )
        assert response.status_code == 422

    def test_create_habit_invalid_frequency(self):
        """Негативный тест: неправильное значение frequency"""
        response = client.post(
            "/habits",
            json={"name": "Test", "description": "Test", "frequency": "hourly"},
        )
        assert response.status_code == 422

    def test_create_habit_negative_target_count(self):
        """Негативный тест: отрицательное значение target_count"""
        response = client.post(
            "/habits",
            json={
                "name": "Test Habit",
                "description": "Test",
                "frequency": "daily",
                "target_count": -5,
            },
        )
        assert response.status_code == 422

    def test_create_habit_target_count_too_large(self):
        """Негативный тест: слишком большое значение target_count"""
        response = client.post(
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

    def setup_method(self):
        """Создание тестовой привычки перед каждым тестом"""
        response = client.post(
            "/habits",
            json={
                "name": "Test Habit for Tracking",
                "description": "Test",
                "frequency": "daily",
            },
        )
        assert response.status_code == 201
        self.habit_id = response.json()["id"]

    def test_track_habit_future_date(self):
        """Негативный тест: дата в будущем"""
        from datetime import date, timedelta

        future_date = (date.today() + timedelta(days=1)).isoformat()

        response = client.post(
            f"/habits/{self.habit_id}/track",
            json={"habit_id": self.habit_id, "completed_date": future_date, "count": 1},
        )
        assert response.status_code == 422
        data = response.json()
        # Проверяем что в массиве ошибок есть сообщение о будущей дате
        error_messages = " ".join(
            err["message"].lower() for err in data.get("errors", [])
        )
        assert "будущем" in error_messages or "future" in error_messages

    def test_track_habit_invalid_count(self):
        """Негативный тест: неправильное количество"""
        response = client.post(
            f"/habits/{self.habit_id}/track",
            json={"habit_id": self.habit_id, "count": 0},
        )
        assert response.status_code == 422

    def test_track_habit_count_too_large(self):
        """Негативный тест: слишком большое количество"""
        response = client.post(
            f"/habits/{self.habit_id}/track",
            json={"habit_id": self.habit_id, "count": 101},
        )
        assert response.status_code == 422

    def test_track_habit_xss_in_notes(self):
        """Негативный тест: XSS в заметках"""
        response = client.post(
            f"/habits/{self.habit_id}/track",
            json={
                "habit_id": self.habit_id,
                "count": 1,
                "notes": "<script>alert('xss')</script>",
            },
        )
        assert response.status_code == 422

    def test_track_nonexistent_habit(self):
        """Негативный тест: несуществующая привычка"""
        response = client.post(
            "/habits/99999/track", json={"habit_id": 99999, "count": 1}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["type"] == "https://api.habittracker.dev/errors/not-found"
        assert "correlation_id" in data


class TestErrorResponses:
    """Тесты формата ответов об ошибках (RFC 7807)"""

    def test_not_found_error_format(self):
        """Проверка формата ошибки 404"""
        response = client.get("/items/99999")
        assert response.status_code == 404

        data = response.json()
        # Проверка обязательных полей RFC 7807
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert data["status"] == 404
        assert "detail" in data
        assert "instance" in data
        assert "correlation_id" in data

    def test_validation_error_format(self):
        """Проверка формата ошибки валидации"""
        response = client.post("/habits", json={"name": ""})
        assert response.status_code == 422

        data = response.json()
        assert "type" in data
        assert "validation" in data["type"]
        assert "correlation_id" in data
        assert data["status"] == 422

    def test_correlation_id_uniqueness(self):
        """Проверка уникальности correlation_id"""
        response1 = client.get("/items/99999")
        response2 = client.get("/items/99998")

        correlation_id1 = response1.json()["correlation_id"]
        correlation_id2 = response2.json()["correlation_id"]

        assert correlation_id1 != correlation_id2


class TestItemsValidation:
    """Тесты валидации для items (учебный пример)"""

    def test_create_item_valid(self):
        """Позитивный тест: создание элемента"""
        response = client.post("/items", json={"name": "Test Item"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Item"
        assert "id" in data

    def test_create_item_empty_name(self):
        """Негативный тест: пустое имя"""
        response = client.post("/items", json={"name": ""})
        assert response.status_code == 422

    def test_create_item_name_too_long(self):
        """Негативный тест: слишком длинное имя"""
        response = client.post("/items", json={"name": "A" * 101})
        assert response.status_code == 422

    def test_create_item_xss_attempt(self):
        """Негативный тест: попытка XSS"""
        response = client.post("/items", json={"name": "<script>alert(1)</script>"})
        assert response.status_code == 422


class TestBoundaryValues:
    """Тесты граничных значений"""

    def test_habit_name_min_length(self):
        """Граничное значение: имя минимальной длины"""
        response = client.post(
            "/habits", json={"name": "A", "description": "", "frequency": "daily"}
        )
        assert response.status_code == 201

    def test_habit_name_max_length(self):
        """Граничное значение: имя максимальной длины"""
        response = client.post(
            "/habits",
            json={"name": "A" * 100, "description": "", "frequency": "daily"},
        )
        assert response.status_code == 201

    def test_habit_description_max_length(self):
        """Граничное значение: описание максимальной длины"""
        response = client.post(
            "/habits",
            json={"name": "Test", "description": "A" * 500, "frequency": "daily"},
        )
        assert response.status_code == 201

    def test_tracking_count_min(self):
        """Граничное значение: минимальное количество"""
        # Сначала создать привычку
        habit_response = client.post(
            "/habits", json={"name": "Test", "frequency": "daily"}
        )
        habit_id = habit_response.json()["id"]

        response = client.post(
            f"/habits/{habit_id}/track", json={"habit_id": habit_id, "count": 1}
        )
        assert response.status_code == 201

    def test_tracking_count_max(self):
        """Граничное значение: максимальное количество"""
        habit_response = client.post(
            "/habits", json={"name": "Test", "frequency": "daily"}
        )
        habit_id = habit_response.json()["id"]

        response = client.post(
            f"/habits/{habit_id}/track", json={"habit_id": habit_id, "count": 100}
        )
        assert response.status_code == 201
