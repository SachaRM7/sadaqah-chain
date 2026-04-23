from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import Database


def test_database_created_with_expected_tables(tmp_path):
    db = Database(tmp_path / "schema.db")

    with db.connection() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }

    assert {"users", "charities", "donations", "ledger", "polls", "poll_votes", "settings", "admin_log"}.issubset(tables)
