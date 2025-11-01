"""
Тесты для Habit Tracker API с JWT аутентификацией
"""


class TestHabits:
    """Тесты для создания и получения привычек"""

    def test_create_habit_success(self, authenticated_client):
        """Успешное создание привычки"""
        response = authenticated_client.post(
            "/habits",
            json={
                "name": "Пить воду",
                "description": "Выпивать 8 стаканов воды в день",
                "frequency": "daily",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Пить воду"

    def test_create_habit_unauthorized(self, test_client):
        """Создание привычки без авторизации"""
        response = test_client.post("/habits", json={"name": "Test", "frequency": "daily"})
        assert response.status_code == 401

    def test_get_habits(self, authenticated_client):
        """Получение списка привычек"""
        response = authenticated_client.get("/habits")
        assert response.status_code == 200
        data = response.json()
        assert "habits" in data
        assert "total" in data
        assert isinstance(data["habits"], list)
