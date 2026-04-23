from __future__ import annotations

import asyncio
from hashlib import sha256

from charities import CharityCreate, CharityService
from db import Database, now_iso
from i18n import t
from ledger import LedgerService
from polls import PollService
from reports import WeeklyReportService
from zakat_calculator import CalculationInput, ZakatCalculator

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:  # pragma: no cover
    Application = None
    CommandHandler = None
    ContextTypes = None
    Update = object


class SadaqahChainBot:
    def __init__(self, token: str, admin_user_ids: list[int], db: Database):
        if Application is None:
            raise RuntimeError("python-telegram-bot is required to run the bot")
        self.db = db
        self.admin_user_ids = set(admin_user_ids)
        self.ledger = LedgerService(db)
        self.charities = CharityService(db, self.ledger)
        self.polls = PollService(db)
        self.reports = WeeklyReportService(db)
        self.calculator = ZakatCalculator()
        self.application = Application.builder().token(token).build()
        self._register_handlers()

    def _register_handlers(self) -> None:
        handlers = {
            "start": self.start,
            "zakat": self.zakat,
            "calculate": self.calculate,
            "charities": self.list_charities,
            "ledger": self.list_ledger,
            "donate": self.donate,
            "mydonations": self.my_donations,
            "export": self.export_ledger,
            "admin": self.admin,
            "poll": self.poll,
        }
        for name, handler in handlers.items():
            self.application.add_handler(CommandHandler(name, handler))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_message(t("en", "welcome"))

    async def zakat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        result = self.calculator.calculate(CalculationInput(cash_savings={"USD": 100000}, preferred_currency="USD"))
        await update.effective_chat.send_message(f"Quick example Zakat due: {result.zakat_due} {result.preferred_currency}")

    async def calculate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        amount = float(context.args[0]) if context.args else 0.0
        result = self.calculator.calculate(CalculationInput(cash_savings={"USD": amount}, preferred_currency="USD"))
        await update.effective_chat.send_message(f"Estimated Zakat due: {result.zakat_due} {result.preferred_currency}")

    async def list_charities(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        charities = self.charities.list_charities()
        if not charities:
            await update.effective_chat.send_message("No charities are currently whitelisted.")
            return
        text = "\n".join(f"#{item['id']} {item['name_en']} ({item['category']})" for item in charities)
        await update.effective_chat.send_message(text)

    async def list_ledger(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        entries = self.ledger.list_entries(limit=10)
        if not entries:
            await update.effective_chat.send_message("Ledger is empty.")
            return
        text = "\n".join(f"#{entry['entry_id']} {entry['type']} {entry['amount']} {entry['currency']}" for entry in entries)
        await update.effective_chat.send_message(text)

    async def donate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if len(context.args) < 2:
            await update.effective_chat.send_message("Usage: /donate <charity_id> <amount>")
            return
        charity_id = int(context.args[0])
        amount = float(context.args[1])
        user_hash = self._hash_user(update.effective_user.id)
        donation = self.db.create_donation(
            {
                "user_id_hash": user_hash,
                "charity_id": charity_id,
                "amount": amount,
                "currency": "USD",
                "campaign_tag": None,
                "notes": "telegram donation record",
                "created_at": now_iso(),
            }
        )
        self.ledger.record_entry("donation_received", amount, "USD", from_user_hash=user_hash, to_charity_id=charity_id, notes="telegram donation record")
        await update.effective_chat.send_message(f"Donation recorded with id {donation['id']}")

    async def my_donations(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_hash = self._hash_user(update.effective_user.id)
        donations = self.db.list_donations(user_id_hash=user_hash)
        if not donations:
            await update.effective_chat.send_message("No donations found for your profile.")
            return
        text = "\n".join(f"#{item['id']} -> charity {item['charity_id']}: {item['amount']} {item['currency']}" for item in donations)
        await update.effective_chat.send_message(text)

    async def export_ledger(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_chat.send_document(document=self.ledger.export_csv().encode("utf-8"), filename="ledger.csv")

    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user.id not in self.admin_user_ids:
            await update.effective_chat.send_message(t("en", "admin_only"))
            return
        if not self.charities.list_charities():
            self.charities.add_charity(
                CharityCreate(
                    name_en="Starter Water Fund",
                    name_ar="صندوق الماء",
                    category="water",
                    website="https://example.org",
                    verification_status="verified",
                    added_by="telegram-admin",
                )
            )
        await update.effective_chat.send_message("Admin panel ready. Use the API key endpoints for full administration.")

    async def poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        poll = self.polls.create_poll("Which campaign should be funded next?", ["Water", "Food", "Medical"], "telegram-admin")
        await update.effective_chat.send_poll(question=poll["question"], options=poll["options"], is_anonymous=False)

    def _hash_user(self, user_id: int) -> str:
        return sha256(str(user_id).encode("utf-8")).hexdigest()[:16]

    async def run(self) -> None:
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
