from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str = ""
    admin_user_ids: List[int] = field(default_factory=list)
    api_key: str = "dev-api-key"
    chat_id: str = ""
    database_path: Path = Path("data/sadaqahchain.db")
    backup_dir: Path = Path("backups")
    preferred_currency: str = "USD"
    nisab_api_url: str = "https://api.exchangerate.host/latest"
    host: str = "127.0.0.1"
    port: int = 8000
    poll_channel_id: str = ""
    weekly_report_day: str = "fri"
    weekly_report_hour_utc: int = 14


def _parse_admin_ids(value: str) -> List[int]:
    if not value.strip():
        return []
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def load_settings(env_file: str | None = None) -> Settings:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    database_path = Path(os.getenv("DATABASE_PATH", "data/sadaqahchain.db"))
    backup_dir = Path(os.getenv("BACKUP_DIR", "backups"))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_user_ids=_parse_admin_ids(os.getenv("ADMIN_USER_IDS", "")),
        api_key=os.getenv("API_KEY", "dev-api-key"),
        chat_id=os.getenv("CHAT_ID", ""),
        database_path=database_path,
        backup_dir=backup_dir,
        preferred_currency=os.getenv("PREFERRED_CURRENCY", "USD"),
        nisab_api_url=os.getenv("NISAB_API_URL", "https://api.exchangerate.host/latest"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        poll_channel_id=os.getenv("POLL_CHANNEL_ID", ""),
        weekly_report_day=os.getenv("WEEKLY_REPORT_DAY", "fri"),
        weekly_report_hour_utc=int(os.getenv("WEEKLY_REPORT_HOUR_UTC", "14")),
    )
