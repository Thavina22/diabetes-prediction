"""HTTP-level tests via FastAPI TestClient (stateless mode, auth bypassed)."""

import pytest
from fastapi.testclient import TestClient

SCREENING_PAYLOAD = {
    "glucose_mg_dl": 126,
    "glucose_type": "fasting",
    "sbp": 130,
    "dbp": 85,
    "height_cm": 175,
    "weight_kg": 88,
    "ldl_mg_dl": 130,
    "hdl_mg_dl": 38,
    "triglycerides_mg_dl": 180,
    "age": 52,
    "sex": "M",
    "family_history": True,
}


@pytest.fixture(scope="module")
def client():
    from main import app

    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_feature_flags_endpoint(client: TestClient):
    response = client.get("/api/v1/features")
    assert response.status_code == 200
    assert any(flag["key"] == "fhir_export" for flag in response.json()["flags"])


def test_screening_creates_result(client: TestClient):
    response = client.post("/api/v1/screening", json=SCREENING_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert 0 <= body["health_score"] <= 100
    assert body["risk_category"] in {"low", "medium", "high", "very_high"}
    assert body["ml_result"]["score"] is not None


def test_screening_rejects_dbp_above_sbp(client: TestClient):
    payload = {**SCREENING_PAYLOAD, "sbp": 110, "dbp": 120}
    response = client.post("/api/v1/screening", json=payload)
    assert response.status_code == 422


def test_export_fhir_and_cda(client: TestClient):
    fhir = client.post("/api/v1/export/fhir", json=SCREENING_PAYLOAD)
    assert fhir.status_code == 200
    assert "application/fhir+json" in fhir.headers["content-type"]
    assert len(fhir.json()["entry"]) >= 6

    cda = client.post("/api/v1/export/cda", json=SCREENING_PAYLOAD)
    assert cda.status_code == 200
    assert "ClinicalDocument" in cda.text


def test_export_pdf(client: TestClient):
    response = client.post("/api/v1/export/pdf", json=SCREENING_PAYLOAD)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_history_is_empty_without_database(client: TestClient):
    response = client.get("/api/v1/history")
    assert response.status_code == 200
    assert response.json()["screenings"] == []


def test_third_party_requires_api_key(client: TestClient):
    response = client.post("/api/v1/third-party/screening", json=SCREENING_PAYLOAD)
    assert response.status_code == 401


def test_api_key_listing_without_database(client: TestClient):
    response = client.get("/api/v1/third-party/api-keys")
    assert response.status_code == 200
    assert response.json() == []


def test_clerk_webhook_unconfigured_returns_503(client: TestClient):
    response = client.post("/api/v1/webhooks/clerk", json={"type": "user.created"})
    assert response.status_code == 503
