from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import _HABITS_DB, app

client = TestClient(app)


def setup_function():
    """Очистка базы данных перед каждым тестом"""
    _HABITS_DB["habits"].clear()
    _HABITS_DB["tracking_records"].clear()
    _HABITS_DB["next_habit_id"] = 1
    _HABITS_DB["next_record_id"] = 1


class TestHabits:
    """Тесты для создания и получения привычек"""

    def test_create_habit_success(self):
        setup_function()

        response = client.post(
            "/habits",
            params={
                "name": "Пить воду",
                "description": "Выпивать 8 стаканов воды в день",
                "frequency": "daily",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 1
        assert data["name"] == "Пить воду"
        assert data["description"] == "Выпивать 8 стаканов воды в день"
        assert data["frequency"] == "daily"
        assert data["is_active"] is True
        assert "created_at" in data

    def test_create_habit_minimal(self):
        setup_function()

        response = client.post("/habits", params={"name": "Медитация"})

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Медитация"
        assert data["description"] == ""
        assert data["frequency"] == "daily"

    def test_create_habit_validation_errors(self):
        setup_function()

        response = client.post("/habits", params={"name": ""})
        assert response.status_code == 422
        assert "Habit name cannot be empty" in response.json()["error"]["message"]

        long_name = "a" * 101
        response = client.post("/habits", params={"name": long_name})
        assert response.status_code == 422
        assert "less than 100 characters" in response.json()["error"]["message"]

        long_description = "a" * 501
        response = client.post(
            "/habits", params={"name": "Test", "description": long_description}
        )
        assert response.status_code == 422
        assert "less than 500 characters" in response.json()["error"]["message"]

    def test_get_habits_empty(self):
        setup_function()

        response = client.get("/habits")

        assert response.status_code == 200
        data = response.json()
        assert data["habits"] == []
        assert data["total"] == 0

    def test_get_habits_with_data(self):
        setup_function()

        client.post("/habits", params={"name": "Привычка 1"})
        client.post("/habits", params={"name": "Привычка 2"})
        client.post("/habits", params={"name": "Привычка 3"})

        response = client.get("/habits")

        assert response.status_code == 200
        data = response.json()
        assert len(data["habits"]) == 3
        assert data["total"] == 3

    def test_get_habits_active_filter(self):
        setup_function()

        client.post("/habits", params={"name": "Активная привычка"})

        habit2_resp = client.post("/habits", params={"name": "Неактивная привычка"})
        habit2_id = habit2_resp.json()["id"]

        client.put(f"/habits/{habit2_id}", json={"is_active": False})

        response = client.get("/habits?active_only=true")
        assert response.status_code == 200
        assert len(response.json()["habits"]) == 1

        response = client.get("/habits?active_only=false")
        assert response.status_code == 200
        assert len(response.json()["habits"]) == 2


class TestHabitTracking:
    """Тесты для отслеживания привычек"""

    def test_track_habit_success(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Упражнения"})
        habit_id = habit_resp.json()["id"]

        response = client.post(f"/habits/{habit_id}/track")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Habit tracked successfully"
        assert data["record"]["habit_id"] == habit_id
        assert data["record"]["completed_at"] == date.today().isoformat()

    def test_track_habit_with_custom_date(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Чтение"})
        habit_id = habit_resp.json()["id"]

        custom_date = "2025-09-24"
        response = client.post(
            f"/habits/{habit_id}/track", params={"completed_at": custom_date}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["record"]["completed_at"] == custom_date

    def test_track_habit_duplicate_date(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        response1 = client.post(f"/habits/{habit_id}/track")
        assert response1.status_code == 200

        response2 = client.post(f"/habits/{habit_id}/track")
        assert response2.status_code == 200
        assert "already tracked" in response2.json()["message"]

    def test_track_habit_not_found(self):
        setup_function()

        response = client.post("/habits/999/track")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_track_inactive_habit(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        client.put(f"/habits/{habit_id}", json={"is_active": False})

        response = client.post(f"/habits/{habit_id}/track")

        assert response.status_code == 400
        assert "inactive_habit" in response.json()["error"]["code"]

    def test_track_habit_invalid_date_format(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        response = client.post(
            f"/habits/{habit_id}/track", params={"completed_at": "invalid-date"}
        )

        assert response.status_code == 422
        assert "Invalid date format" in response.json()["error"]["message"]


class TestHabitStats:
    """Тесты для статистики привычек"""

    def test_get_habit_stats_empty(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Новая привычка"})
        habit_id = habit_resp.json()["id"]

        response = client.get(f"/habits/{habit_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["completed_days"] == 0
        assert data["stats"]["completion_rate"] == 0.0
        assert data["stats"]["current_streak"] == 0
        assert data["stats"]["longest_streak"] == 0

    def test_get_habit_stats_with_data(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        today = date.today()
        yesterday = today - timedelta(days=1)

        client.post(
            f"/habits/{habit_id}/track", params={"completed_at": today.isoformat()}
        )
        client.post(
            f"/habits/{habit_id}/track", params={"completed_at": yesterday.isoformat()}
        )

        response = client.get(f"/habits/{habit_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["completed_days"] == 2
        assert data["stats"]["current_streak"] == 2
        assert data["stats"]["longest_streak"] == 2

    def test_get_habit_stats_different_periods(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        for period in ["week", "month", "year"]:
            response = client.get(f"/habits/{habit_id}/stats?period={period}")
            assert response.status_code == 200
            assert response.json()["period"] == period

    def test_get_habit_stats_invalid_period(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        response = client.get(f"/habits/{habit_id}/stats?period=invalid")

        assert response.status_code == 422
        assert "week, month, year" in response.json()["error"]["message"]

    def test_get_habit_stats_not_found(self):
        setup_function()

        response = client.get("/habits/999/stats")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestHabitUpdate:
    """Тесты для обновления привычек"""

    def test_update_habit_name(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Старое имя"})
        habit_id = habit_resp.json()["id"]

        response = client.put(f"/habits/{habit_id}", json={"name": "Новое имя"})

        assert response.status_code == 200
        data = response.json()
        assert data["habit"]["name"] == "Новое имя"
        assert "name" in data["message"]

    def test_update_habit_multiple_fields(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        update_data = {
            "name": "Обновленная привычка",
            "description": "Новое описание",
            "frequency": "weekly",
            "is_active": False,
        }

        response = client.put(f"/habits/{habit_id}", json=update_data)

        assert response.status_code == 200
        habit = response.json()["habit"]
        assert habit["name"] == "Обновленная привычка"
        assert habit["description"] == "Новое описание"
        assert habit["frequency"] == "weekly"
        assert habit["is_active"] is False
        assert "updated_at" in habit

    def test_update_habit_no_fields(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        response = client.put(f"/habits/{habit_id}", json={})

        assert response.status_code == 200
        assert "No fields to update" in response.json()["message"]

    def test_update_habit_validation_errors(self):
        setup_function()

        habit_resp = client.post("/habits", params={"name": "Привычка"})
        habit_id = habit_resp.json()["id"]

        response = client.put(f"/habits/{habit_id}", json={"name": ""})
        assert response.status_code == 422

        response = client.put(f"/habits/{habit_id}", json={"name": "a" * 101})
        assert response.status_code == 422

        response = client.put(f"/habits/{habit_id}", json={"description": "a" * 501})
        assert response.status_code == 422

    def test_update_habit_not_found(self):
        setup_function()

        response = client.put("/habits/999", json={"name": "Test"})

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
