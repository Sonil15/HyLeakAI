"""Contract tests for the public API without loading model artifacts."""

from fastapi.testclient import TestClient

from api.main import app


def test_health_is_available_without_artifacts():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}


def test_live_endpoints_explain_missing_artifacts():
    with TestClient(app) as client:
        response = client.get("/v1/simulations")
    assert response.status_code in {200, 503}


def test_field_and_metadata_routes_are_registered():
    with TestClient(app) as client:
        metadata = client.get("/v1/metadata")
        fields = client.get("/v1/fields/0?timestep=30")
    assert metadata.status_code in {200, 503}
    assert fields.status_code in {200, 422, 503}
