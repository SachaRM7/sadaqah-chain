from __future__ import annotations

import json
from typing import Any

from db import Database


class PollService:
    def __init__(self, db: Database):
        self.db = db

    def create_poll(self, question: str, options: list[str], created_by: str, closes_at: str | None = None) -> dict[str, Any]:
        if len(options) < 2:
            raise ValueError("A poll needs at least two options")
        return self._normalize(self.db.create_poll(question, options, created_by, closes_at))

    def list_polls(self, status: str | None = None) -> list[dict[str, Any]]:
        return [self._normalize(row) for row in self.db.list_polls(status=status)]

    def vote(self, poll_id: int, user_id_hash: str, option_index: int) -> dict[str, Any]:
        self.db.upsert_vote(poll_id, user_id_hash, option_index)
        return self.results(poll_id)

    def results(self, poll_id: int) -> dict[str, Any]:
        polls = [poll for poll in self.list_polls() if poll["id"] == poll_id]
        if not polls:
            raise ValueError(f"Unknown poll {poll_id}")
        poll = polls[0]
        tally = self.db.tally_votes(poll_id)
        return {
            "poll_id": poll_id,
            "question": poll["question"],
            "options": poll["options"],
            "tally": {poll["options"][index]: count for index, count in tally.items()},
        }

    @staticmethod
    def _normalize(row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        row["options"] = json.loads(row.pop("options_json"))
        return row
