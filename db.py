from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_SQL = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA_SQL)

    def backup(self, destination: str | Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        return destination

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now_iso()),
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def create_charity(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO charities(name_ar, name_en, category, website, wallet_address, verification_status, added_date, added_by, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    payload["name_ar"],
                    payload["name_en"],
                    payload["category"],
                    payload["website"],
                    payload.get("wallet_address"),
                    payload["verification_status"],
                    payload["added_date"],
                    payload["added_by"],
                ),
            )
            row = conn.execute("SELECT * FROM charities WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def list_charities(self, active_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM charities"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY id ASC"
        with self.connection() as conn:
            rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]

    def get_charity(self, charity_id: int) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM charities WHERE id = ?", (charity_id,)).fetchone()
        return dict(row) if row else None

    def remove_charity(self, charity_id: int) -> bool:
        with self.connection() as conn:
            cursor = conn.execute("UPDATE charities SET is_active = 0 WHERE id = ?", (charity_id,))
        return cursor.rowcount > 0

    def create_donation(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO donations(user_id_hash, charity_id, amount, currency, campaign_tag, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["user_id_hash"],
                    payload["charity_id"],
                    payload["amount"],
                    payload["currency"],
                    payload.get("campaign_tag"),
                    payload.get("notes"),
                    payload["created_at"],
                ),
            )
            row = conn.execute("SELECT * FROM donations WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def list_donations(self, user_id_hash: str | None = None, charity_id: int | None = None) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if user_id_hash:
            clauses.append("user_id_hash = ?")
            params.append(user_id_hash)
        if charity_id is not None:
            clauses.append("charity_id = ?")
            params.append(charity_id)
        query = "SELECT * FROM donations"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def create_poll(self, question: str, options: list[str], created_by: str, closes_at: str | None = None) -> dict[str, Any]:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO polls(question, options_json, status, created_by, created_at, closes_at)
                VALUES (?, ?, 'active', ?, ?, ?)
                """,
                (question, json.dumps(options, ensure_ascii=False), created_by, now_iso(), closes_at),
            )
            row = conn.execute("SELECT * FROM polls WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def list_polls(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM polls"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY id DESC"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def upsert_vote(self, poll_id: int, user_id_hash: str, option_index: int) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO poll_votes(poll_id, user_id_hash, option_index, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(poll_id, user_id_hash)
                DO UPDATE SET option_index = excluded.option_index, created_at = excluded.created_at
                """,
                (poll_id, user_id_hash, option_index, now_iso()),
            )

    def tally_votes(self, poll_id: int) -> dict[int, int]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT option_index, COUNT(*) AS total FROM poll_votes WHERE poll_id = ? GROUP BY option_index",
                (poll_id,),
            ).fetchall()
        return {row["option_index"]: row["total"] for row in rows}

    def log_admin_action(self, action: str, actor: str, target_type: str, target_id: str | None = None, details: str | None = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO admin_log(action, actor, target_type, target_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (action, actor, target_type, target_id, details, now_iso()),
            )


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
