"""Тесты для health check endpoint"""


def test_health_check(test_client):
    """Health check endpoint должен возвращать статус OK"""
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_no_auth_required(test_client):
    """Health check не требует авторизации"""
    # Убедимся что нет заголовка Authorization
    headers = test_client.headers.copy()
    if "Authorization" in headers:
        del headers["Authorization"]

    response = test_client.get("/health", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
