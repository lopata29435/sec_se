"""Тесты для обработки ошибок и формата RFC 7807"""


class TestErrorResponses:
    """Тесты формата ответов об ошибках (RFC 7807)"""

    def test_not_found_error_format(self, authenticated_client):
        """Проверка формата ошибки 404"""
        response = authenticated_client.get("/items/99999")
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

    def test_validation_error_format(self, authenticated_client):
        """Проверка формата ошибки валидации"""
        response = authenticated_client.post("/habits", json={"name": ""})
        assert response.status_code == 422

        data = response.json()
        assert "type" in data
        assert "validation" in data["type"]
        assert "correlation_id" in data
        assert data["status"] == 422

    def test_correlation_id_uniqueness(self, authenticated_client):
        """Проверка уникальности correlation_id"""
        response1 = authenticated_client.get("/items/99999")
        response2 = authenticated_client.get("/items/99998")

        correlation_id1 = response1.json()["correlation_id"]
        correlation_id2 = response2.json()["correlation_id"]

        assert correlation_id1 != correlation_id2

    def test_unauthorized_error(self, test_client):
        """Проверка ошибки 401 при отсутствии токена"""
        response = test_client.get("/habits")
        assert response.status_code == 401

    def test_health_endpoint_no_auth_required(self, test_client):
        """Health endpoint не требует авторизации"""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestItemsValidation:
    """Тесты валидации для items (учебный пример)"""

    def test_create_item_valid(self, authenticated_client):
        """Позитивный тест: создание элемента"""
        response = authenticated_client.post("/items", json={"name": "Test Item"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Item"
        assert "id" in data

    def test_create_item_empty_name(self, authenticated_client):
        """Негативный тест: пустое имя"""
        response = authenticated_client.post("/items", json={"name": ""})
        assert response.status_code == 422

    def test_create_item_name_too_long(self, authenticated_client):
        """Негативный тест: слишком длинное имя"""
        response = authenticated_client.post("/items", json={"name": "A" * 101})
        assert response.status_code == 422

    def test_create_item_xss_attempt(self, authenticated_client):
        """Негативный тест: попытка XSS"""
        response = authenticated_client.post("/items", json={"name": "<script>alert(1)</script>"})
        assert response.status_code == 422

    def test_get_item_not_found(self, authenticated_client):
        """Негативный тест: несуществующий элемент"""
        response = authenticated_client.get("/items/99999")
        assert response.status_code == 404
        data = response.json()
        assert data["type"] == "https://api.habittracker.dev/errors/not-found"
        assert "correlation_id" in data
