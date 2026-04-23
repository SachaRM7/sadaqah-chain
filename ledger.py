from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Any

from db import Database, now_iso


class LedgerService:
    def __init__(self, db: Database):
        self.db = db

    def record_entry(
        self,
        entry_type: str,
        amount: float,
        currency: str,
        from_user_hash: str | None = None,
        to_charity_id: int | None = None,
        campaign_tag: str | None = None,
        notes: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        timestamp = timestamp or now_iso()
        previous = self._last_entry()
        previous_signature = previous["signature"] if previous else ""
        payload = {
            "timestamp": timestamp,
            "type": entry_type,
            "amount": round(amount, 2),
            "currency": currency.upper(),
            "from_user_hash": from_user_hash,
            "to_charity_id": to_charity_id,
            "campaign_tag": campaign_tag,
            "notes": notes,
        }
        signature = self.compute_signature(previous_signature, payload)
        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ledger(timestamp, type, amount, currency, from_user_hash, to_charity_id, campaign_tag, notes, previous_signature, signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["timestamp"],
                    payload["type"],
                    payload["amount"],
                    payload["currency"],
                    payload["from_user_hash"],
                    payload["to_charity_id"],
                    payload["campaign_tag"],
                    payload["notes"],
                    previous_signature,
                    signature,
                ),
            )
            row = conn.execute("SELECT * FROM ledger WHERE entry_id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def list_entries(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ledger ORDER BY entry_id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_json(self) -> list[dict[str, Any]]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM ledger ORDER BY entry_id ASC").fetchall()
        return [dict(row) for row in rows]

    def export_csv(self) -> str:
        rows = self.export_json()
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "entry_id",
                "timestamp",
                "type",
                "amount",
                "currency",
                "from_user_hash",
                "to_charity_id",
                "campaign_tag",
                "notes",
                "previous_signature",
                "signature",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def verify_chain(self) -> bool:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM ledger ORDER BY entry_id ASC").fetchall()
        previous_signature = ""
        for row in rows:
            payload = {
                "timestamp": row["timestamp"],
                "type": row["type"],
                "amount": row["amount"],
                "currency": row["currency"],
                "from_user_hash": row["from_user_hash"],
                "to_charity_id": row["to_charity_id"],
                "campaign_tag": row["campaign_tag"],
                "notes": row["notes"],
            }
            expected = self.compute_signature(previous_signature, payload)
            if row["previous_signature"] != previous_signature or row["signature"] != expected:
                return False
            previous_signature = row["signature"]
        return True

    def _last_entry(self) -> dict[str, Any] | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM ledger ORDER BY entry_id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    @staticmethod
    def compute_signature(previous_signature: str, payload: dict[str, Any]) -> str:
        serialized = json.dumps({"previous_signature": previous_signature, **payload}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
