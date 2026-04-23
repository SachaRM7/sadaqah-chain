from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from charities import CharityCreate, CharityService
from config import Settings, load_settings
from db import Database, now_iso
from ledger import LedgerService
from polls import PollService
from reports import WeeklyReportService
from zakat_calculator import CalculationInput, NisabThresholds, ZakatCalculator


class ZakatRequest(BaseModel):
    cash_savings: dict[str, float] = Field(default_factory=dict)
    gold_grams: float = 0.0
    gold_karat: int = 24
    silver_grams: float = 0.0
    silver_karat: int = 24
    equities_value: float = 0.0
    business_equity: float = 0.0
    crypto_totals: dict[str, float] = Field(default_factory=dict)
    debts_owed_to_you: float = 0.0
    liabilities: float = 0.0
    preferred_currency: str = "USD"
    exchange_rates: dict[str, float] = Field(default_factory=dict)


class DonationRequest(BaseModel):
    user_id_hash: str
    charity_id: int
    amount: float
    currency: str = "USD"
    campaign_tag: str | None = None
    notes: str | None = None


class PollRequest(BaseModel):
    question: str
    options: list[str]
    created_by: str = "admin"
    closes_at: str | None = None


class CharityRequest(BaseModel):
    name_en: str
    name_ar: str
    category: str
    website: str
    verification_status: str
    added_by: str
    wallet_address: str | None = None


def create_app(db: Database | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    db = db or Database(Path(settings.database_path))
    ledger = LedgerService(db)
    charity_service = CharityService(db, ledger)
    poll_service = PollService(db)
    report_service = WeeklyReportService(db)
    calculator = ZakatCalculator(NisabThresholds(base_currency=settings.preferred_currency))

    app = FastAPI(title="SadaqahChain", version="1.0.0")
    app.state.db = db
    app.state.ledger = ledger
    app.state.charity_service = charity_service
    app.state.poll_service = poll_service
    app.state.report_service = report_service
    app.state.calculator = calculator
    app.state.settings = settings

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/nisab")
    def get_nisab() -> dict[str, Any]:
        nisab = calculator.nisab
        return {
            "base_currency": nisab.base_currency,
            "gold_nisab_grams": nisab.gold_nisab_grams,
            "silver_nisab_grams": nisab.silver_nisab_grams,
            "gold_nisab_value": nisab.gold_nisab_value,
            "silver_nisab_value": nisab.silver_nisab_value,
            "effective_threshold": nisab.effective_threshold,
        }

    @app.post("/api/v1/calculate")
    def calculate(payload: ZakatRequest) -> dict[str, Any]:
        result = calculator.calculate(CalculationInput(**payload.model_dump()))
        return result.to_dict()

    @app.get("/api/v1/charities")
    def list_charities() -> list[dict[str, Any]]:
        return charity_service.list_charities()

    @app.get("/api/v1/charities/{charity_id}")
    def get_charity(charity_id: int) -> dict[str, Any]:
        charity = charity_service.get_charity(charity_id)
        if not charity:
            raise HTTPException(status_code=404, detail="Charity not found")
        return charity

    @app.post("/api/v1/charities")
    def add_charity(payload: CharityRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
        return charity_service.add_charity(CharityCreate(**payload.model_dump()))

    @app.post("/api/v1/donations")
    def create_donation(payload: DonationRequest) -> dict[str, Any]:
        if not charity_service.get_charity(payload.charity_id):
            raise HTTPException(status_code=404, detail="Charity not found")
        donation = db.create_donation({**payload.model_dump(), "created_at": now_iso()})
        ledger.record_entry(
            entry_type="donation_received",
            amount=payload.amount,
            currency=payload.currency,
            from_user_hash=payload.user_id_hash,
            to_charity_id=payload.charity_id,
            campaign_tag=payload.campaign_tag,
            notes=payload.notes,
        )
        return donation

    @app.get("/api/v1/donations")
    def list_donations(user_id_hash: str | None = None, charity_id: int | None = None) -> list[dict[str, Any]]:
        return db.list_donations(user_id_hash=user_id_hash, charity_id=charity_id)

    @app.get("/api/v1/ledger")
    def list_ledger(limit: int = Query(default=50, le=500), offset: int = 0) -> dict[str, Any]:
        items = ledger.list_entries(limit=limit, offset=offset)
        return {"items": items, "limit": limit, "offset": offset, "count": len(items)}

    @app.get("/api/v1/ledger/export")
    def export_ledger(format: str = "json"):
        if format == "csv":
            return PlainTextResponse(ledger.export_csv(), media_type="text/csv")
        return JSONResponse(ledger.export_json())

    @app.get("/api/v1/polls")
    def list_polls(status: str | None = None) -> list[dict[str, Any]]:
        return poll_service.list_polls(status=status)

    @app.post("/api/v1/polls")
    def create_poll(payload: PollRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
        return poll_service.create_poll(payload.question, payload.options, payload.created_by, payload.closes_at)

    @app.get("/api/v1/reports/weekly")
    def weekly_report() -> dict[str, Any]:
        return report_service.generate_report()

    return app


app = create_app()
