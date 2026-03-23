from __future__ import annotations

from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import keyboards
from .content import ContentCatalog
from .storage import Storage
from .utils import compact_name


class FollowupScheduler:
    def __init__(
        self,
        bot: Bot,
        storage: Storage,
        content: ContentCatalog,
        timezone: str,
    ):
        self.bot = bot
        self.storage = storage
        self.content = content
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))

    def start(self) -> None:
        if self.scheduler.running:
            return
        self.scheduler.add_job(self._dispatch_due_reminders, "interval", minutes=5)
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _dispatch_due_reminders(self) -> None:
        for reminder in self.storage.get_due_reminders():
            template = self.content.text(
                f"reminders.{reminder['reminder_type']}",
                user_name=compact_name(reminder.get("first_name")),
            )
            if not template:
                self.storage.mark_reminder_sent(int(reminder["id"]), failed=True)
                continue
            try:
                await self._send_or_update_panel(reminder["telegram_id"], template)
                self.storage.mark_reminder_sent(int(reminder["id"]))
            except Exception:
                self.storage.mark_reminder_sent(int(reminder["id"]), failed=True)

    async def _send_or_update_panel(self, telegram_id: int, text: str) -> None:
        panel = self.storage.get_panel(telegram_id)
        markup = keyboards.home_keyboard(False)
        if panel:
            try:
                await self.bot.edit_message_text(
                    chat_id=panel["chat_id"],
                    message_id=panel["message_id"],
                    text=text,
                    reply_markup=markup,
                )
                return
            except TelegramBadRequest:
                pass
        sent = await self.bot.send_message(telegram_id, text, reply_markup=markup)
        self.storage.save_panel(telegram_id, sent.chat.id, sent.message_id)
