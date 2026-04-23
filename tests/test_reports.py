from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from charities import CharityCreate, CharityService
from db import Database
from ledger import LedgerService
from reports import WeeklyReportService


def test_weekly_report_summarises_received_and_categories(tmp_path):
    db = Database(tmp_path / "reports.db")
    ledger = LedgerService(db)
    charities = CharityService(db, ledger)
    charity = charities.add_charity(
        CharityCreate(
            name_en="Relief Fund",
            name_ar="صندوق الإغاثة",
            category="medical",
            website="https://example.org",
            verification_status="verified",
            added_by="admin",
        )
    )
    db.create_donation(
        {
            "user_id_hash": "abc",
            "charity_id": charity["id"],
            "amount": 150.0,
            "currency": "USD",
            "campaign_tag": "urgent",
            "notes": "weekly support",
            "created_at": "2026-04-23T10:00:00+00:00",
        }
    )
    ledger.record_entry("donation_received", 150.0, "USD", from_user_hash="abc", to_charity_id=charity["id"])

    report = WeeklyReportService(db).generate_report()

    assert report["total_received_this_week"] == 150.0
    assert report["breakdown_by_charity_category"]["medical"] == 150.0
