from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import create_app
from charities import CharityCreate
from db import Database
from ledger import LedgerService


def build_client(tmp_path):
    db = Database(tmp_path / "api.db")
    LedgerService(db)
    app = create_app(db)
    return TestClient(app), db


def test_health_endpoint(tmp_path):
    client, _ = build_client(tmp_path)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_calculate_endpoint(tmp_path):
    client, _ = build_client(tmp_path)

    response = client.post(
        "/api/v1/calculate",
        json={
            "cash_savings": {"USD": 100000},
            "preferred_currency": "USD",
        },
    )

    assert response.status_code == 200
    assert response.json()["zakat_due"] == 2500.0


def test_charities_endpoint_returns_non_empty_list(tmp_path):
    client, db = build_client(tmp_path)
    charity_service = app_state_service(db)
    charity_service.add_charity(
        CharityCreate(
            name_en="Water Aid",
            name_ar="ماء",
            category="water",
            website="https://example.org",
            verification_status="verified",
            added_by="admin",
        )
    )

    response = client.get("/api/v1/charities")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name_en"] == "Water Aid"


def app_state_service(db):
    app = create_app(db)
    return app.state.charity_service
