from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from db import Database
from ledger import LedgerService

ALLOWED_CATEGORIES = {"hunger", "education", "medical", "emergency", "orphanage", "water"}
ALLOWED_STATUSES = {"pending", "verified", "rejected"}
FORBIDDEN_KEYWORDS = {"gambling", "alcohol", "riba"}


@dataclass(slots=True)
class CharityCreate:
    name_en: str
    name_ar: str
    category: str
    website: str
    verification_status: str
    added_by: str
    wallet_address: str | None = None
    added_date: str = date.today().isoformat()


class CharityService:
    def __init__(self, db: Database, ledger: LedgerService | None = None):
        self.db = db
        self.ledger = ledger

    def add_charity(self, payload: CharityCreate) -> dict[str, Any]:
        self._validate(payload)
        record = self.db.create_charity(asdict(payload))
        self.db.log_admin_action("charity_add", payload.added_by, "charity", str(record["id"]), record["name_en"])
        if self.ledger:
            self.ledger.record_entry("charity_added", 0.0, "USD", notes=record["name_en"], to_charity_id=record["id"])
        return record

    def list_charities(self) -> list[dict[str, Any]]:
        return self.db.list_charities(active_only=True)

    def get_charity(self, charity_id: int) -> dict[str, Any] | None:
        return self.db.get_charity(charity_id)

    def remove_charity(self, charity_id: int, actor: str) -> bool:
        removed = self.db.remove_charity(charity_id)
        if removed:
            self.db.log_admin_action("charity_remove", actor, "charity", str(charity_id))
            if self.ledger:
                self.ledger.record_entry("charity_removed", 0.0, "USD", notes=f"charity_id={charity_id}", to_charity_id=charity_id)
        return removed

    def _validate(self, payload: CharityCreate) -> None:
        if payload.category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Unsupported charity category: {payload.category}")
        if payload.verification_status not in ALLOWED_STATUSES:
            raise ValueError(f"Unsupported verification status: {payload.verification_status}")
        text = " ".join([payload.name_en, payload.name_ar, payload.website]).lower()
        forbidden = [keyword for keyword in FORBIDDEN_KEYWORDS if keyword in text]
        if forbidden:
            raise ValueError(f"Charity payload contains forbidden sharia keywords: {forbidden}")
