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


def test_site_screen_uses_user_scalars_without_model_artifacts():
    with TestClient(app) as client:
        response = client.post("/v1/site-screen", json={
            "area_km2": 25, "reservoir_thickness_m": 80, "porosity_fraction": 0.18,
            "storage_efficiency_fraction": 0.04, "co2_density_kg_m3": 650,
            "depth_m": 1800, "brine_density_kg_m3": 1050,
            "allowable_overpressure_bar": 50, "injection_rate_mtpa": 1,
            "injection_years": 20, "caprock_thickness_m": 120,
        })
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]["capacity_mt_co2"] == 9.36
    assert payload["results"]["planned_mass_mt_co2"] == 20


def test_assessment_contract_declares_traceability_fields():
    schema = app.openapi()["paths"]["/v1/assessments"]["post"]
    assert schema["summary"] == "Assessment"
