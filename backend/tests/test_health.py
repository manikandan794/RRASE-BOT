def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert "health" in body


def test_health_endpoint_reports_status(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "app_name" in body
    assert "app_env" in body
    assert isinstance(body["database"], bool)
