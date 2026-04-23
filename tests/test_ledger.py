from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import Database
from ledger import LedgerService


def test_ledger_hash_chain_validates_and_detects_tampering(tmp_path):
    db = Database(tmp_path / "ledger.db")
    ledger = LedgerService(db)

    first = ledger.record_entry(entry_type="charity_added", amount=0.0, currency="USD", notes="seed")
    second = ledger.record_entry(entry_type="donation_received", amount=100.0, currency="USD", notes="donation")

    assert first["entry_id"] == 1
    assert second["entry_id"] == 2
    assert ledger.verify_chain() is True

    with db.connection() as conn:
        conn.execute("UPDATE ledger SET amount = 999 WHERE entry_id = 2")

    assert ledger.verify_chain() is False
