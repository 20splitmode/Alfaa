from __future__ import annotations

import asyncio

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, MenuButtonWebApp, WebAppInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from .agent_offer_pdf import ensure_agent_offer_pdf
from .config import Settings
from .content import ContentCatalog
from .handlers import BusinessStartHandlers
from .integrations import IntegrationService
from .keyboards import MINI_APP_URL
from .product_catalog import ProductCatalog
from .scheduler import FollowupScheduler
from .storage import Storage


class BusinessStartBot:
    def __init__(self, settings: Settings):
        self.settings = settings
        try:
            ensure_agent_offer_pdf(settings.agent_offer_path)
        except ModuleNotFoundError:
            pass
        self.bot = Bot(settings.telegram_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dispatcher = Dispatcher(storage=MemoryStorage())
        self.storage = Storage(settings)
        self.content = ContentCatalog(settings.content_path)
        self.catalog = ProductCatalog(settings.product_catalog_path)
        self.integrations = IntegrationService(settings)
        self.handlers = BusinessStartHandlers(
            bot=self.bot,
            settings=settings,
            storage=self.storage,
            content=self.content,
            integrations=self.integrations,
            catalog=self.catalog,
        )
        self.dispatcher.include_router(self.handlers.router)
        self.scheduler = FollowupScheduler(self.bot, self.storage, self.content, settings.timezone)

    async def _set_commands(self) -> None:
        default_commands = [
            BotCommand(command="start", description="Открыть бот"),
            BotCommand(command="menu", description="Главный экран"),
            BotCommand(command="help", description="О боте"),
            BotCommand(command="agent", description="Агентский доступ"),
        ]
        await self.bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())
        admin_commands = default_commands + [BotCommand(command="admin", description="Админ-панель")]
        for admin_id in self.settings.admin_ids:
            await self.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        await self.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Мини-апп",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        )

    async def start(self) -> None:
        self.scheduler.start()
        try:
            await self._set_commands()
            if self.settings.use_webhook:
                await self._start_webhook()
            else:
                await self.bot.delete_webhook(drop_pending_updates=False)
                await self.dispatcher.start_polling(
                    self.bot,
                    allowed_updates=self.dispatcher.resolve_used_update_types(),
                )
        finally:
            self.scheduler.stop()
            self.storage.close()
            await self.integrations.close()
            await self.bot.session.close()

    async def _start_webhook(self) -> None:
        await self.bot.set_webhook(self.settings.webhook_url, drop_pending_updates=False)
        app = web.Application()
        app.router.add_get("/healthz", self._healthcheck)
        SimpleRequestHandler(self.dispatcher, self.bot).register(app, path=self.settings.webhook_path)
        setup_application(app, self.dispatcher, bot=self.bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=self.settings.webhook_host, port=self.settings.webhook_port)
        await site.start()
        try:
            await asyncio.Future()
        finally:
            await self.bot.delete_webhook(drop_pending_updates=False)
            await runner.cleanup()

    async def _healthcheck(self, _: web.Request) -> web.Response:
        return web.json_response({"ok": True, "bot": self.settings.bot_name})
