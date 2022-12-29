from fastapi.testclient import TestClient

from sciety_discovery.main import create_app


def test_read_main():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
