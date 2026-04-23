from __future__ import annotations

import asyncio
from contextlib import suppress

import uvicorn

from api import create_app
from config import load_settings
from cron_jobs import build_scheduler
from db import Database
from sadaqahchain import SadaqahChainBot


async def main() -> None:
    settings = load_settings()
    db = Database(settings.database_path)
    scheduler = build_scheduler(db, settings.backup_dir)
    scheduler.start()

    app = create_app(db=db, settings=settings)
    config = uvicorn.Config(app, host=settings.host, port=settings.port, log_level="info")
    server = uvicorn.Server(config)

    tasks = [asyncio.create_task(server.serve(), name="fastapi-server")]
    if settings.bot_token:
        bot = SadaqahChainBot(settings.bot_token, settings.admin_user_ids, db)
        tasks.append(asyncio.create_task(bot.run(), name="telegram-bot"))

    try:
        await asyncio.gather(*tasks)
    finally:
        scheduler.shutdown(wait=False)
        for task in tasks:
            task.cancel()
        with suppress(asyncio.CancelledError):
            await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
