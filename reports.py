from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from db import Database


class WeeklyReportService:
    def __init__(self, db: Database):
        self.db = db

    def generate_report(self, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        since = (now - timedelta(days=7)).replace(microsecond=0).isoformat()
        with self.db.connection() as conn:
            donation_rows = conn.execute(
                """
                SELECT d.amount, d.currency, c.category, c.name_en
                FROM donations d
                JOIN charities c ON c.id = d.charity_id
                WHERE d.created_at >= ?
                """,
                (since,),
            ).fetchall()
            ledger_rows = conn.execute(
                "SELECT type, amount, currency FROM ledger WHERE timestamp >= ?",
                (since,),
            ).fetchall()
        total_received = round(sum(row["amount"] for row in ledger_rows if row["type"] == "donation_received"), 2)
        total_disbursed = round(sum(row["amount"] for row in ledger_rows if row["type"] == "donation_disbursed"), 2)
        category_breakdown: dict[str, float] = defaultdict(float)
        top_campaigns: dict[str, float] = defaultdict(float)
        for row in donation_rows:
            category_breakdown[row["category"]] += row["amount"]
            top_campaigns[row["name_en"]] += row["amount"]
        ordered_campaigns = sorted(top_campaigns.items(), key=lambda item: item[1], reverse=True)
        return {
            "generated_at": now.replace(microsecond=0).isoformat(),
            "total_received_this_week": total_received,
            "total_disbursed_this_week": total_disbursed,
            "breakdown_by_charity_category": {key: round(value, 2) for key, value in category_breakdown.items()},
            "top_voted_campaigns_funded": [name for name, _ in ordered_campaigns[:3]],
            "ledger_link_hint": "/api/v1/ledger/export",
        }

    def format_report_text(self, report: dict[str, Any]) -> str:
        lines = [
            "SadaqahChain weekly disbursement report",
            f"Generated at: {report['generated_at']}",
            f"Total received this week: {report['total_received_this_week']}",
            f"Total disbursed this week: {report['total_disbursed_this_week']}",
            "Breakdown by charity category:",
        ]
        for category, amount in report["breakdown_by_charity_category"].items():
            lines.append(f"- {category}: {amount}")
        if report["top_voted_campaigns_funded"]:
            lines.append("Top campaigns funded:")
            lines.extend(f"- {name}" for name in report["top_voted_campaigns_funded"])
        lines.append(f"Ledger: {report['ledger_link_hint']}")
        return "\n".join(lines)
