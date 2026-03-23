from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InputMediaPhoto, Message

from . import keyboards
from .agent_exam import (
    EXAM_DURATION_MINUTES,
    EXAM_VERSION,
    PASSING_SCORE,
    QUESTION_COUNT,
    RETRY_COOLDOWN_HOURS,
    build_exam,
    progress_bar,
    score_exam,
)
from .agent_offer_pdf import DOCUMENT_VERSION
from .antifraud import (
    agent_level_label,
    agent_status_label,
    fraud_reason_label,
    lead_fraud_status_label,
    score_lead,
)
from .config import Settings
from .content import ContentCatalog
from .integrations import IntegrationService
from .product_catalog import ProductCatalog
from .storage import Storage
from .utils import escape_html, extract_start_argument, json_loads, normalize_phone, now_utc, parse_iso, parse_tracking_payload


LEAD_STATUS_LABELS = {
    "new": "новый",
    "active": "активный",
    "interested": "заинтересован",
    "submitted": "отправил заявку",
    "in_review": "в обработке",
    "confirmed": "подтверждён",
    "lost": "потерян",
    "recontact": "повторный контакт",
}

DIAGNOSTIC_ORDER = ["payment_method", "legal_status", "activity_format"]

DIAGNOSTIC_QUESTIONS: dict[str, dict[str, Any]] = {
    "payment_method": {
        "step": "1/3",
        "progress": "■□□",
        "text": "<b>Бизнес-диагностика</b>\n\nШаг {step} {progress}\n\nКак вы сейчас принимаете оплату?",
        "options": [
            {"id": "card_transfers", "title": "Карта / переводы"},
            {"id": "cash", "title": "Наличные"},
            {"id": "business_account", "title": "Через ИП / ООО"},
            {"id": "none", "title": "Пока не принимаю"},
        ],
    },
    "legal_status": {
        "step": "2/3",
        "progress": "■■□",
        "text": "<b>Бизнес-диагностика</b>\n\nШаг {step} {progress}\n\nЕсть ли зарегистрированный статус?",
        "options": [
            {"id": "none", "title": "Нет"},
            {"id": "self_employed", "title": "Самозанятый"},
            {"id": "ip", "title": "ИП"},
            {"id": "ooo", "title": "ООО"},
        ],
    },
    "activity_format": {
        "step": "3/3",
        "progress": "■■■",
        "text": "<b>Бизнес-диагностика</b>\n\nШаг {step} {progress}\n\nВаш основной формат работы:",
        "options": [
            {"id": "services", "title": "Услуги"},
            {"id": "marketplaces", "title": "Торговля / маркетплейсы"},
            {"id": "freelance", "title": "Фриланс"},
            {"id": "mixed", "title": "Смешанный"},
        ],
    },
}

PAYMENT_LABELS = {
    "card_transfers": "карта и переводы",
    "cash": "наличные",
    "business_account": "через ИП или ООО",
    "none": "оплата пока не принимается",
}

LEGAL_STATUS_LABELS = {
    "none": "бизнес пока не зарегистрирован",
    "self_employed": "есть самозанятость",
    "ip": "есть ИП",
    "ooo": "есть ООО",
}

ACTIVITY_LABELS = {
    "services": "услуги",
    "marketplaces": "торговля и маркетплейсы",
    "freelance": "фриланс",
    "mixed": "смешанный формат",
}

NEARBY_KIND_LABELS = {
    "atm": "банкоматы",
    "branch": "отделения",
}

SEGMENT_LABELS = {
    "undetermined": "не определился",
    "just_starting": "старт без регистрации",
    "self_employed": "самозанятый",
    "have_ip": "оформленный бизнес",
}

AGENT_INTERVIEW_ORDER = [
    "experience",
    "traffic_source",
    "source_details",
    "audience",
    "expected_volume",
    "rules",
]

AGENT_INTERVIEW_QUESTIONS: dict[str, dict[str, Any]] = {
    "experience": {
        "step": "1/6",
        "progress": "■□□□□□",
        "text": "<b>Собеседование агента</b>\n\nШаг {step} {progress}\n\nКакой у вас опыт в трафике или партнёрских продажах?",
        "options": [
            {"id": "none", "title": "Опыта нет"},
            {"id": "some", "title": "Есть базовый опыт"},
            {"id": "pro", "title": "Есть подтверждённый опыт"},
        ],
    },
    "traffic_source": {
        "step": "2/6",
        "progress": "■■□□□□",
        "text": "<b>Собеседование агента</b>\n\nШаг {step} {progress}\n\nЧерез какой канал вы планируете приводить людей?",
        "options": [
            {"id": "telegram", "title": "Telegram / чаты / каналы"},
            {"id": "content", "title": "Сайт / блог / SEO"},
            {"id": "ads", "title": "Реклама / performance"},
            {"id": "sales", "title": "Личные продажи / комьюнити"},
        ],
    },
    "expected_volume": {
        "step": "5/6",
        "progress": "■■■■■□",
        "text": "<b>Собеседование агента</b>\n\nШаг {step} {progress}\n\nКакой объём обращений вы ожидаете в месяц?",
        "options": [
            {"id": "up_to_10", "title": "До 10"},
            {"id": "10_50", "title": "10–50"},
            {"id": "50_100", "title": "50–100"},
            {"id": "100_plus", "title": "100+"},
        ],
    },
    "rules": {
        "step": "6/6",
        "progress": "■■■■■■",
        "text": "<b>Собеседование агента</b>\n\nШаг {step} {progress}\n\nПодтвердите правила: не обещать одобрение, не выдавать себя за банк, не использовать спам и мотивированный трафик.",
        "options": [
            {"id": "agree", "title": "Подтверждаю"},
            {"id": "disagree", "title": "Не подтверждаю"},
        ],
    },
}

AGENT_INTERVIEW_LABELS = {
    "experience": {
        "none": "опыта нет",
        "some": "есть базовый опыт",
        "pro": "есть подтверждённый опыт",
    },
    "traffic_source": {
        "telegram": "Telegram / чаты / каналы",
        "content": "сайт / блог / SEO",
        "ads": "реклама / performance",
        "sales": "личные продажи / комьюнити",
    },
    "expected_volume": {
        "up_to_10": "до 10 в месяц",
        "10_50": "10–50 в месяц",
        "50_100": "50–100 в месяц",
        "100_plus": "100+ в месяц",
    },
    "rules": {
        "agree": "правила подтверждены",
        "disagree": "правила не подтверждены",
    },
}


class AddressStates(StatesGroup):
    query = State()


class GeoStates(StatesGroup):
    atm = State()
    branch = State()


class LeadStates(StatesGroup):
    name = State()
    phone = State()
    city = State()


class DiagnosticStates(StatesGroup):
    payment_method = State()
    legal_status = State()
    activity_format = State()


class AgentApplicationStates(StatesGroup):
    source_details = State()
    audience = State()


class BusinessStartHandlers:
    def __init__(
        self,
        *,
        bot: Bot,
        settings: Settings,
        storage: Storage,
        content: ContentCatalog,
        integrations: IntegrationService,
        catalog: ProductCatalog,
    ):
        self.bot = bot
        self.settings = settings
        self.storage = storage
        self.content = content
        self.integrations = integrations
        self.catalog = catalog
        self.process_started_at = now_utc()
        self.router = Router()
        self._register()

    def _register(self) -> None:
        r = self.router
        r.message.register(self.start_handler, CommandStart())
        r.message.register(self.menu_handler, Command("menu"))
        r.message.register(self.help_command, Command("help"))
        r.message.register(self.admin_command, Command("admin"))
        r.message.register(self.agent_command, Command("agent"))

        r.callback_query.register(self.nav_callback, F.data.startswith("nav:"))
        r.callback_query.register(self.catalog_callback, F.data.startswith("catalog:"))
        r.callback_query.register(self.product_callback, F.data.startswith("product:"))
        r.callback_query.register(self.picker_callback, F.data.startswith("picker:"))
        r.callback_query.register(self.industry_callback, F.data.startswith("industry:"))
        r.callback_query.register(self.info_callback, F.data.startswith("info:"))
        r.callback_query.register(self.maps_callback, F.data.startswith("maps:"))
        r.callback_query.register(self.currency_callback, F.data.startswith("currency:"))
        r.callback_query.register(self.tariff_callback, F.data.startswith("tariff:"))
        r.callback_query.register(self.diagnostic_callback, F.data.startswith("diagnostic:"))
        r.callback_query.register(self.applications_callback, F.data.startswith("applications:"))
        r.callback_query.register(self.lead_callback, F.data.startswith("lead:"))
        r.callback_query.register(self.admin_callback, F.data.startswith("admin:"))
        r.callback_query.register(self.agent_callback, F.data.startswith("agent:"))
        r.callback_query.register(self.agent_question_callback, F.data.startswith("agentq:"))
        r.callback_query.register(self.agent_exam_callback, F.data.startswith("agentexam:"))

        r.message.register(self.location_handler, F.location)
        r.message.register(self.geo_waiting_handler, StateFilter(GeoStates.atm, GeoStates.branch))
        r.message.register(self.address_handler, AddressStates.query)
        r.message.register(self.lead_name_handler, LeadStates.name)
        r.message.register(self.lead_phone_handler, LeadStates.phone)
        r.message.register(self.lead_city_handler, LeadStates.city)
        r.message.register(self.agent_source_details_handler, AgentApplicationStates.source_details)
        r.message.register(self.agent_audience_handler, AgentApplicationStates.audience)

        r.message.register(self.menu_text_handler, F.text == "В меню")
        r.message.register(self.fallback_handler)

    async def start_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        start_argument = extract_start_argument(message.text)
        referral_agent = self.storage.get_agent_by_code(start_argument)
        tracking = parse_tracking_payload("" if referral_agent and "=" not in start_argument else start_argument)
        user = self.storage.get_or_create_user(
            message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            first_name=message.from_user.first_name,
            tracking=tracking,
        )
        if referral_agent:
            attached_agent = self.storage.attach_referral(message.from_user.id, start_argument)
            if attached_agent:
                self.storage.log_event(
                    "referral_attributed",
                    user_id=user["id"],
                    payload={"agent_id": attached_agent["id"], "referral_code": start_argument},
                )
        self.storage.log_event("start", user_id=user["id"], payload=tracking)
        await state.clear()
        await self._show_screen(
            message.from_user.id,
            "welcome",
            self._home_keyboard(message.from_user.id, message.from_user.username),
            source=message,
            force_new=True,
        )

    async def menu_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        self.storage.get_or_create_user(
            message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            first_name=message.from_user.first_name,
        )
        await state.clear()
        await self._open_home(message.from_user.id, message.from_user.username, source=message)

    async def help_command(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        await state.clear()
        await self._show_panel(message.from_user.id, self.content.text("screens.help"), self._help_keyboard(), source=message)

    async def admin_command(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if not self._is_admin(message.from_user.id, message.from_user.username):
            await self._show_panel(message.from_user.id, self.content.text("errors.admin_only"), self._help_keyboard(), source=message, force_new=True)
            return
        await state.clear()
        await self._show_panel(message.from_user.id, self.content.text("screens.admin_intro"), keyboards.admin_keyboard(), source=message)

    async def agent_command(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        self.storage.get_or_create_user(
            message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            first_name=message.from_user.first_name,
        )
        await state.clear()
        await self._show_agent_panel(message.from_user.id, source=message)

    async def nav_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        await self._open_home(callback.from_user.id, callback.from_user.username, source=callback)

    async def catalog_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        page = int(callback.data.split(":")[2])
        product_ids = self.catalog.catalog_page(page)
        items = [self._catalog_item(product_id) for product_id in product_ids]
        total_next = bool(self.catalog.catalog_page(page + 1))
        await self._show_panel(
            callback.from_user.id,
            self.content.text("screens.catalog"),
            keyboards.catalog_keyboard(items, page, has_prev=page > 0, has_next=total_next),
            source=callback,
        )

    async def product_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        product_id = callback.data.split(":")[2]
        product = self.catalog.get_product(product_id)
        if not product:
            await self._show_panel(callback.from_user.id, self.content.text("screens.api_fallback"), self._help_keyboard(), source=callback)
            return
        self.storage.update_user(callback.from_user.id, scenario=product_id)
        if product_id == "help":
            await self._show_panel(callback.from_user.id, self.content.text("screens.product_help"), self._help_keyboard(), source=callback)
            return
        benefits = self._bullets(product.get("benefits") or [])
        documents = self._bullets(product.get("documents") or [])
        official_url = product.get("official_url") or "https://alfabank.ru/sme/"
        primary_url = self.settings.offer_url or product.get("apply_url") or official_url
        await self._show_panel(
            callback.from_user.id,
            self.content.text(
                "screens.product_detail",
                title=product.get("title"),
                short=product.get("short"),
                for_whom=product.get("for_whom"),
                benefits=benefits,
                documents=documents,
            ),
            keyboards.product_keyboard(
                product_id,
                primary_url,
                official_url,
            ),
            source=callback,
        )

    async def picker_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        parts = callback.data.split(":")
        action = parts[1]
        if action == "page":
            page = int(parts[2])
            situation_ids = self.catalog.situations_page(page)
            items = [self._situation_item(situation_id) for situation_id in situation_ids]
            text_key = "screens.picker" if page == 0 else "screens.picker_more"
            await self._show_panel(
                callback.from_user.id,
                self.content.text(text_key),
                keyboards.picker_keyboard(items, page, has_prev=page > 0, has_next=bool(self.catalog.situations_page(page + 1))),
                source=callback,
            )
            return
        situation_id = parts[2]
        situation = self.catalog.get_situation(situation_id)
        if not situation:
            await self._show_panel(callback.from_user.id, self.content.text("screens.api_fallback"), self._help_keyboard(), source=callback)
            return
        self.storage.update_user(callback.from_user.id, segment=situation_id)
        if situation_id == "industry":
            items = [self._industry_item(industry_id) for industry_id in self.catalog.industries_page()]
            await self._show_panel(
                callback.from_user.id,
                self.content.text("screens.industries"),
                keyboards.industries_keyboard(items),
                source=callback,
            )
            return
        await self._show_recommendation(
            callback.from_user.id,
            title=situation.get("title", ""),
            description=situation.get("description", ""),
            recommended_ids=situation.get("recommended") or [],
            next_step=situation.get("next_step", ""),
            source=callback,
        )

    async def industry_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        industry_id = callback.data.split(":")[2]
        industry = self.catalog.get_industry(industry_id)
        if not industry:
            await self._show_panel(callback.from_user.id, self.content.text("screens.api_fallback"), self._help_keyboard(), source=callback)
            return
        self.storage.update_user(callback.from_user.id, activity=industry_id)
        await self._show_recommendation(
            callback.from_user.id,
            title=industry.get("title", ""),
            description=industry.get("description", ""),
            recommended_ids=industry.get("recommended") or [],
            next_step="Откройте нужный продукт и переходите к оформлению только если задача уже сформулирована.",
            source=callback,
        )

    async def info_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        key = callback.data.split(":")[1]
        allowed = {
            "work",
            "legal",
            "ip_checklist",
            "compare",
            "timeline",
        }
        if key not in allowed:
            await self._show_panel(callback.from_user.id, self.content.text("screens.help"), self._help_keyboard(), source=callback)
            return
        await self._show_panel(
            callback.from_user.id,
            self.content.text(f"screens.info_{key}"),
            self._help_keyboard(),
            source=callback,
        )

    async def maps_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        parts = callback.data.split(":")
        action = parts[1]
        if action == "open":
            await state.clear()
            await self._show_screen(callback.from_user.id, "maps_intro", keyboards.maps_keyboard(), source=callback)
            return
        if action in {"atm", "branch"}:
            await state.clear()
            await state.set_state(GeoStates.atm if action == "atm" else GeoStates.branch)
            await self._show_screen(
                callback.from_user.id,
                "atm_intro" if action == "atm" else "branch_intro",
                keyboards.simple_back_keyboard("maps:open", "К разделу «Рядом»"),
                source=callback,
            )
            return
        if action == "address":
            await state.set_state(AddressStates.query)
            await self._show_screen(callback.from_user.id, "maps_prompt", keyboards.simple_back_keyboard("maps:open", "К карте"), source=callback)
            return
        if action == "alfa":
            user = self.storage.get_user(callback.from_user.id) or {}
            city = user.get("city") or "Москва"
            map_url = self.integrations.alfa_points_search_url(city)
            await self._show_panel(
                callback.from_user.id,
                "Ближайшие точки и адреса можно открыть в Яндекс Картах по вашему городу.",
                keyboards.maps_result_keyboard(map_url, extra_label="Поиск отделений Альфа-Банка", extra_url=map_url),
                source=callback,
            )

    async def currency_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        await self._show_screen(callback.from_user.id, "currency_loading", keyboards.currency_keyboard(), source=callback)
        try:
            rates = await self.integrations.get_currency_rates()
        except Exception as exc:
            self.storage.log_event("api_error", user_id=(self.storage.get_user(callback.from_user.id) or {}).get("id"), payload={"source": "cbr", "error": str(exc)})
            await self._show_screen(callback.from_user.id, "currency_fallback", keyboards.currency_keyboard(), source=callback)
            return
        rate_lines = []
        for code in ("USD", "EUR", "CNY"):
            item = (rates.get("rates") or {}).get(code)
            if not item:
                continue
            rate_lines.append(f"• {code}: {item['value']:.4f} ₽ за {item['nominal']}")
        await self._show_screen(
            callback.from_user.id,
            "currency_result",
            keyboards.currency_keyboard(),
            source=callback,
            rate_date=rates.get("date", ""),
            rates_text="\n".join(rate_lines) or "Курсы не получены.",
        )

    async def diagnostic_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        parts = callback.data.split(":")
        action = parts[1]
        if action == "start":
            await state.clear()
            await state.set_state(DiagnosticStates.payment_method)
            await state.update_data(diagnostic={})
            await self._show_diagnostic_question(callback.from_user.id, "payment_method", source=callback)
            return
        if action != "answer" or len(parts) < 4:
            return
        question_key = parts[2]
        answer_key = parts[3]
        data = await state.get_data()
        diagnostic = dict(data.get("diagnostic") or {})
        diagnostic[question_key] = answer_key
        await state.update_data(diagnostic=diagnostic)
        self.storage.save_quiz_answer(callback.from_user.id, f"diagnostic_{question_key}", answer_key, self._diagnostic_answer_label(question_key, answer_key))
        try:
            current_index = DIAGNOSTIC_ORDER.index(question_key)
        except ValueError:
            current_index = -1
        next_index = current_index + 1
        if next_index < len(DIAGNOSTIC_ORDER):
            next_key = DIAGNOSTIC_ORDER[next_index]
            next_state = {
                "payment_method": DiagnosticStates.payment_method,
                "legal_status": DiagnosticStates.legal_status,
                "activity_format": DiagnosticStates.activity_format,
            }[next_key]
            await state.set_state(next_state)
            await self._show_diagnostic_question(callback.from_user.id, next_key, source=callback)
            return
        result = self._build_diagnostic_result(diagnostic)
        self.storage.update_user(
            callback.from_user.id,
            payment_method=diagnostic.get("payment_method"),
            status=diagnostic.get("legal_status"),
            activity=diagnostic.get("activity_format"),
            scenario=result["scenario"],
            segment=result["segment"],
            primary_pain=result["primary_pain"],
            journey_stage="ready",
            last_result_at=result["completed_at"],
            quiz_completed_at=result["completed_at"],
        )
        await state.clear()
        await self._show_screen(
            callback.from_user.id,
            "diagnostic_result",
            keyboards.diagnostic_result_keyboard(result["primary_product_id"], result.get("secondary_product_id")),
            source=callback,
            level=result["level"],
            segment_label=result["segment_label"],
            readiness_percent=result["readiness_percent"],
            current_state=result["current_state"],
            recommendation=result["recommendation"],
            why_this=result["why_this"],
            recommended=result["recommended_text"],
            next_step=result["next_step"],
        )

    async def tariff_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        action = callback.data.split(":")[1]
        if action == "open":
            await self._show_panel(callback.from_user.id, self.content.text("screens.tariff_intro"), keyboards.tariff_keyboard(), source=callback)
            return
        rule = self.catalog.tariff_rule(action)
        if not rule:
            await self._show_panel(callback.from_user.id, self.content.text("screens.api_fallback"), keyboards.simple_back_keyboard("catalog:page:0", "К каталогу"), source=callback)
            return
        await self._show_panel(
            callback.from_user.id,
            self.content.text("screens.tariff_result", title=rule.get("title"), when=rule.get("when"), why=rule.get("why")),
            keyboards.external_link_keyboard("Открыть официальный подбор", rule.get("official_url") or "https://alfabank.ru/sme/rko/4steps/"),
            source=callback,
        )

    async def applications_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        await state.clear()
        leads = self.storage.list_user_leads(callback.from_user.id)
        if not leads:
            await self._show_panel(callback.from_user.id, self.content.text("screens.applications_empty"), keyboards.applications_keyboard(), source=callback)
            return
        lines = []
        for lead in leads:
            lines.append(
                f"• #{lead['id']} — {LEAD_STATUS_LABELS.get(lead.get('lead_status') or 'new', lead.get('lead_status') or 'new')}"
            )
        await self._show_panel(
            callback.from_user.id,
            self.content.text("screens.applications_list", applications_text="\n".join(lines)),
            keyboards.applications_keyboard(),
            source=callback,
        )

    async def lead_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        parts = callback.data.split(":")
        action = parts[1]
        if action == "start":
            await state.clear()
            product_id = parts[2]
            await state.update_data(product_id=product_id, lead_started_at=now_utc().isoformat())
            await self._show_panel(callback.from_user.id, self.content.text("screens.lead_consent"), keyboards.consent_keyboard(product_id), source=callback)
            return
        if action == "consent":
            product_id = parts[2]
            decision = parts[3]
            if decision != "yes":
                await state.clear()
                await self._show_panel(callback.from_user.id, self.content.text("screens.lead_cancelled"), keyboards.applications_keyboard(show_new=False), source=callback)
                return
            await state.clear()
            await state.update_data(product_id=product_id, lead_started_at=now_utc().isoformat())
            await state.set_state(LeadStates.name)
            await self._show_panel(callback.from_user.id, self.content.text("screens.lead_name"), keyboards.simple_back_keyboard("nav:home"), source=callback)

    async def agent_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        action = callback.data.split(":")[1]
        if action == "panel":
            await state.clear()
            await self._show_agent_panel(callback.from_user.id, source=callback)
            return
        if action == "apply":
            await self._start_agent_interview(callback.from_user.id, source=callback, state=state)
            return
        if action == "confirm_read":
            await state.clear()
            self.storage.mark_agent_offer_confirmed(
                callback.from_user.id,
                document_version=DOCUMENT_VERSION,
            )
            await self._start_agent_exam(callback.from_user.id, source=callback)
            return
        if action == "exam_start":
            await state.clear()
            await self._start_agent_exam(callback.from_user.id, source=callback)
            return

    async def agent_question_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        parts = callback.data.split(":")
        if len(parts) < 3:
            return
        question_key = parts[1]
        answer_key = parts[2]
        data = await state.get_data()
        answers = dict(data.get("agent_application") or {})
        answers[question_key] = answer_key
        await state.update_data(agent_application=answers)

        if question_key == "experience":
            await self._show_agent_interview_choice(callback.from_user.id, "traffic_source", source=callback)
            return
        if question_key == "traffic_source":
            await state.set_state(AgentApplicationStates.source_details)
            await self._show_panel(
                callback.from_user.id,
                self.content.text("screens.agent_interview_source_details"),
                keyboards.simple_back_keyboard("nav:home", "В меню"),
                source=callback,
            )
            return
        if question_key == "expected_volume":
            await self._show_agent_interview_choice(callback.from_user.id, "rules", source=callback)
            return
        if question_key == "rules":
            if answer_key != "agree":
                await state.clear()
                await self._show_panel(
                    callback.from_user.id,
                    self.content.text("screens.agent_rules_declined"),
                    self._help_keyboard(),
                    source=callback,
                )
                return
            await self._begin_agent_offer_review(callback.from_user.id, state=state, source=callback)
            return

    async def agent_exam_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user:
            return
        await callback.answer()
        parts = callback.data.split(":")
        if len(parts) != 5 or parts[1] != "answer":
            return
        attempt_id = int(parts[2])
        question_index = int(parts[3])
        answer_key = parts[4]
        attempt = self.storage.get_agent_exam_attempt(attempt_id)
        if not attempt or int(attempt.get("telegram_id") or 0) != int(callback.from_user.id):
            await callback.answer("Сессия не найдена", show_alert=True)
            return
        if await self._expire_agent_exam_if_needed(attempt):
            await self._show_agent_panel(callback.from_user.id, source=callback)
            return
        if str(attempt.get("status") or "") != "in_progress":
            await callback.answer("Тест уже завершён", show_alert=True)
            return
        questions = json_loads(attempt.get("questions_json"), [])
        answers = list(json_loads(attempt.get("answers_json"), []))
        if question_index != len(answers):
            await callback.answer("Этот шаг уже закрыт", show_alert=True)
            return
        if question_index >= len(questions):
            await callback.answer("Тест уже завершён", show_alert=True)
            return
        answers.append(answer_key)
        attempt = self.storage.update_agent_exam_attempt_answers(attempt_id, answers) or attempt
        if len(answers) >= len(questions):
            await self._finish_agent_exam(attempt_id, source=callback)
            return
        await self._show_agent_exam_question(callback.from_user.id, attempt_id, source=callback)

    async def admin_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        if not callback.from_user or not self._is_admin(callback.from_user.id, callback.from_user.username):
            if callback.from_user:
                await callback.answer("Недоступно", show_alert=True)
            return
        await callback.answer()
        await state.clear()
        parts = callback.data.split(":")
        action = parts[1]
        if action == "panel":
            await self._show_panel(callback.from_user.id, self.content.text("screens.admin_intro"), keyboards.admin_keyboard(), source=callback)
            return
        if action == "users":
            users = self.storage.recent_users()
            users_text = "\n".join(
                f"• {escape_html(user.get('first_name') or user.get('full_name') or str(user['telegram_id']))} — {escape_html(user.get('segment') or 'без сегмента')}"
                for user in users
            ) or "Пока нет пользователей."
            await self._show_panel(callback.from_user.id, self.content.text("screens.admin_users", users_text=users_text), keyboards.admin_keyboard(), source=callback)
            return
        if action == "activity":
            activity = self.storage.recent_activity_by_day()
            activity_text = "\n".join(f"• {item['day']}: {item['events_count']}" for item in activity) or "События пока не зафиксированы."
            await self._show_panel(callback.from_user.id, self.content.text("screens.admin_activity", activity_text=activity_text), keyboards.admin_keyboard(), source=callback)
            return
        if action == "api":
            errors = self.storage.recent_api_errors()
            api_text = "\n".join(f"• {item['created_at']} — {item['payload_json']}" for item in errors) or "Ошибок API пока нет."
            await self._show_panel(callback.from_user.id, self.content.text("screens.admin_api", api_text=api_text), keyboards.admin_keyboard(), source=callback)
            return
        if action == "sources":
            sources = self.storage.traffic_summary()
            lines = [
                f"• {escape_html(item['source_key'])}: {item['users_count']} пользователей / {item['leads_count']} лидов"
                for item in sources
            ] or ["Источники пока не определены."]
            await self._show_panel(
                callback.from_user.id,
                self.content.text("screens.admin_sources", summary_text="\n".join(lines)),
                keyboards.admin_keyboard(),
                source=callback,
            )
            return
        if action == "dropoff":
            stages = self.storage.stage_summary()
            lines = [
                f"Стартов: {stages.get('started', 0)}",
                f"Диагностика завершена: {stages.get('diagnostic_completed', 0)}",
                f"Результат сформирован: {stages.get('result_ready', 0)}",
                f"Лидов создано: {stages.get('lead_sent', 0)}",
                "",
                "Текущий этап пользователя:",
            ]
            for key, label in (
                ("new", "новый"),
                ("ready", "готов к следующему шагу"),
                ("lead_sent", "лид отправлен"),
            ):
                lines.append(f"• {label}: {stages.get(key, 0)}")
            await self._show_panel(
                callback.from_user.id,
                self.content.text("screens.admin_dropoff", summary_text="\n".join(lines)),
                keyboards.admin_keyboard(),
                source=callback,
            )
            return
        if action == "quality":
            summary = self.storage.quality_summary()
            lines = ["По статусу качества:"]
            for item in summary["by_fraud"]:
                lines.append(f"• {lead_fraud_status_label(item['fraud_status'])}: {item['count']}")
            lines.append("")
            lines.append(f"Одобрено агентов: {summary['approved_agents']}")
            lines.append(f"Заявок на агентский доступ: {summary['pending_agents']}")
            if summary["suspicious_agents"]:
                lines.append("")
                lines.append("Подозрительные агенты:")
                for item in summary["suspicious_agents"]:
                    name = item.get("first_name") or item.get("full_name") or f"agent#{item['id']}"
                    lines.append(
                        f"• #{item['id']} {escape_html(name)} — reject {int(item['rejected_leads'] or 0)}/{int(item['total_leads'] or 0)}"
                    )
            await self._show_panel(
                callback.from_user.id,
                self.content.text("screens.admin_quality", summary_text="\n".join(lines)),
                keyboards.admin_keyboard(),
                source=callback,
            )
            return
        if action == "csv":
            path = self.storage.export_leads_csv()
            if callback.message:
                await callback.message.answer_document(FSInputFile(path), caption="CSV по заявкам")
            return
        if action == "csv_agents":
            path = self.storage.export_agents_csv()
            if callback.message:
                await callback.message.answer_document(FSInputFile(path), caption="CSV по агентам")
            return
        if action == "funnel":
            summary = self.storage.funnel_summary()
            branches = self.storage.branch_conversion()
            lines = [
                f"Пользователей: {summary['total_users']}",
                f"Активных за 7 дней: {summary['active_users']}",
                f"Заявок: {summary['leads_total']}",
                "",
                "По статусам:",
            ]
            for item in summary["by_status"]:
                lines.append(f"• {item['lead_status']}: {item['count']}")
            lines.append("")
            lines.append("По сценариям:")
            for item in branches:
                lines.append(f"• {item['scenario']}: {item['users_count']} пользователей / {item['leads_count']} заявок")
            await self._show_panel(callback.from_user.id, self.content.text("screens.admin_funnel", summary_text="\n".join(lines)), keyboards.admin_keyboard(), source=callback)
            return
        if action == "fraud":
            fraud_status = parts[2]
            leads = self.storage.list_leads(fraud_status=fraud_status)
            await self._show_panel(
                callback.from_user.id,
                self._format_admin_leads(leads, f"Качество: {lead_fraud_status_label(fraud_status)}"),
                keyboards.admin_list_keyboard(leads),
                source=callback,
            )
            return
        if action == "leads":
            status = parts[2]
            leads = self.storage.list_leads(status=status)
            await self._show_panel(callback.from_user.id, self._format_admin_leads(leads, f"Статус: {LEAD_STATUS_LABELS.get(status, status)}"), keyboards.admin_list_keyboard(leads), source=callback)
            return
        if action == "agents":
            agent_status = parts[2]
            agents = self.storage.list_agents(agent_status=agent_status)
            title = "Заявки агентов" if agent_status == "pending" else "Черновики агентов" if agent_status == "draft" else "Агенты"
            text = self._format_admin_agents(agents, title)
            await self._show_panel(
                callback.from_user.id,
                text,
                keyboards.admin_agent_list_keyboard(agents),
                source=callback,
            )
            return
        if action == "agent_open":
            agent_id = int(parts[2])
            agent = self.storage.agent_overview(agent_id)
            if agent:
                await self._show_panel(
                    callback.from_user.id,
                    self._format_admin_agent(agent),
                    keyboards.admin_agent_keyboard(agent_id),
                    source=callback,
                )
            return
        if action == "agent_set":
            agent_id = int(parts[2])
            status = parts[3]
            agent = self.storage.set_agent_state(agent_id, agent_status=status, approved_by=callback.from_user.id)
            if agent:
                self.storage.log_event(
                    "admin_agent_status_changed",
                    user_id=agent.get("user_id"),
                    payload={"agent_id": agent_id, "agent_status": status, "admin": callback.from_user.id},
                )
                await self._notify_agent_status_change(agent, status)
                overview = self.storage.agent_overview(agent_id) or agent
                await self._show_panel(
                    callback.from_user.id,
                    self._format_admin_agent(overview),
                    keyboards.admin_agent_keyboard(agent_id),
                    source=callback,
                )
            return
        if action == "agent_level":
            agent_id = int(parts[2])
            level = parts[3]
            agent = self.storage.set_agent_state(agent_id, agent_level=level)
            if agent:
                overview = self.storage.agent_overview(agent_id) or agent
                await self._show_panel(
                    callback.from_user.id,
                    self._format_admin_agent(overview),
                    keyboards.admin_agent_keyboard(agent_id),
                    source=callback,
                )
            return
        if action == "open":
            lead_id = int(parts[2])
            lead = self.storage.get_lead(lead_id)
            if lead:
                await self._show_panel(callback.from_user.id, self._format_admin_lead(lead), keyboards.admin_lead_keyboard(lead_id), source=callback)
            return
        if action == "set":
            lead_id = int(parts[2])
            status = parts[3]
            lead = self.storage.set_lead_state(lead_id, lead_status=status)
            if lead:
                user = self.storage.lead_owner_user(lead_id)
                self.storage.log_event(
                    "admin_lead_status_changed",
                    user_id=(user or {}).get("id"),
                    lead_id=lead_id,
                    payload={"lead_status": status, "admin": callback.from_user.id},
                )
                if user:
                    await self.integrations.send_status_update(user, lead)
                await self._show_panel(callback.from_user.id, self._format_admin_lead(lead), keyboards.admin_lead_keyboard(lead_id), source=callback)
            return
        if action == "fraudset":
            lead_id = int(parts[2])
            fraud_status = parts[3]
            lead = self.storage.set_lead_state(lead_id, fraud_status=fraud_status)
            if lead:
                self.storage.log_event(
                    "admin_lead_quality_changed",
                    user_id=(self.storage.lead_owner_user(lead_id) or {}).get("id"),
                    lead_id=lead_id,
                    payload={"fraud_status": fraud_status, "admin": callback.from_user.id},
                )
                await self._show_panel(
                    callback.from_user.id,
                    self._format_admin_lead(lead),
                    keyboards.admin_lead_keyboard(lead_id),
                    source=callback,
                )

    async def location_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user or not message.location:
            return
        current_state = await state.get_state()
        if current_state == GeoStates.atm.state:
            await state.clear()
            await self._show_nearby_points(message.from_user.id, message.location.latitude, message.location.longitude, kind="atm", source=message)
            return
        if current_state == GeoStates.branch.state:
            await state.clear()
            await self._show_nearby_points(message.from_user.id, message.location.latitude, message.location.longitude, kind="branch", source=message)
            return
        await self._show_panel(
            message.from_user.id,
            self.content.text(
                "screens.maps_result",
                address="Текущая геопозиция",
                lat=message.location.latitude,
                lon=message.location.longitude,
            ),
            keyboards.maps_result_keyboard(
                self.integrations.maps_nearby_url(message.location.latitude, message.location.longitude),
                extra_url=self.integrations.alfa_points_search_url(f"{message.location.latitude},{message.location.longitude}"),
                extra_label="Найти точки Альфа-Банка",
            ),
            source=message,
        )

    async def geo_waiting_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user or message.location:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        current_state = await state.get_state()
        kind = "atm" if current_state == GeoStates.atm.state else "branch"
        text = (message.text or "").strip()
        if len(text) >= 3:
            await state.clear()
            self.storage.update_user(message.from_user.id, city=text)
            try:
                result = await self.integrations.geocode(text)
            except Exception as exc:
                user = self.storage.get_user(message.from_user.id)
                self.storage.log_event(
                    "api_error",
                    user_id=(user or {}).get("id"),
                    payload={"source": "geocoder", "error": str(exc), "query": text, "mode": "geo_waiting"},
                )
                await self._show_panel(
                    message.from_user.id,
                    self.content.text("screens.maps_fallback"),
                    keyboards.maps_result_keyboard(
                        self.integrations.maps_search_url(text),
                        extra_url=self.integrations.alfa_points_search_url(text),
                        extra_label="Найти точки Альфа-Банка",
                    ),
                    source=message,
                )
                return
            if result and result.get("lat") is not None and result.get("lon") is not None:
                await self._show_nearby_points(
                    message.from_user.id,
                    float(result["lat"]),
                    float(result["lon"]),
                    kind=kind,
                    source=message,
                )
                return
            await self._show_panel(
                message.from_user.id,
                self.content.text("screens.maps_fallback"),
                keyboards.maps_result_keyboard(
                    self.integrations.maps_search_url(text),
                    extra_url=self.integrations.alfa_points_search_url(text),
                    extra_label="Найти точки Альфа-Банка",
                ),
                source=message,
            )
            return
        kind_label = "банкоматы" if kind == "atm" else "отделения"
        await self._show_panel(
            message.from_user.id,
            self.content.text("screens.geo_waiting", kind_label=kind_label),
            keyboards.simple_back_keyboard("maps:open", "К разделу «Рядом»"),
            source=message,
        )

    async def address_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        query = (message.text or "").strip()
        if len(query) < 3:
            await self._show_panel(message.from_user.id, self.content.text("errors.invalid_address"), keyboards.maps_keyboard(), source=message)
            return
        self.storage.update_user(message.from_user.id, city=query)
        try:
            result = await self.integrations.geocode(query)
        except Exception as exc:
            user = self.storage.get_user(message.from_user.id)
            self.storage.log_event("api_error", user_id=(user or {}).get("id"), payload={"source": "geocoder", "error": str(exc), "query": query})
            await state.clear()
            await self._show_panel(
                message.from_user.id,
                self.content.text("screens.maps_fallback"),
                keyboards.maps_result_keyboard(
                    self.integrations.maps_search_url(query),
                    extra_url=self.integrations.alfa_points_search_url(query),
                    extra_label="Найти точки Альфа-Банка",
                ),
                source=message,
            )
            return
        await state.clear()
        if not result:
            await self._show_panel(
                message.from_user.id,
                self.content.text("screens.maps_fallback"),
                keyboards.maps_result_keyboard(
                    self.integrations.maps_search_url(query),
                    extra_url=self.integrations.alfa_points_search_url(query),
                    extra_label="Найти точки Альфа-Банка",
                ),
                source=message,
            )
            return
        await self._show_panel(
            message.from_user.id,
            self.content.text(
                "screens.maps_result",
                address=result.get("address", query),
                lat=result.get("lat"),
                lon=result.get("lon"),
            ),
            keyboards.maps_result_keyboard(
                self.integrations.maps_route_url(result.get("lat"), result.get("lon"), query=query),
                extra_url=self.integrations.alfa_points_search_url(result.get("address", query)),
                extra_label="Найти точки Альфа-Банка",
            ),
            source=message,
        )

    async def agent_source_details_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        value = (message.text or "").strip()
        if len(value) < 3:
            await self._show_panel(
                message.from_user.id,
                self.content.text("errors.invalid_agent_source_details"),
                keyboards.simple_back_keyboard("nav:home", "В меню"),
                source=message,
            )
            return
        data = await state.get_data()
        answers = dict(data.get("agent_application") or {})
        answers["source_details"] = value
        await state.update_data(agent_application=answers)
        await state.set_state(AgentApplicationStates.audience)
        await self._show_panel(
            message.from_user.id,
            self.content.text("screens.agent_interview_audience"),
            keyboards.simple_back_keyboard("nav:home", "В меню"),
            source=message,
        )

    async def agent_audience_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        value = (message.text or "").strip()
        if len(value) < 3:
            await self._show_panel(
                message.from_user.id,
                self.content.text("errors.invalid_agent_audience"),
                keyboards.simple_back_keyboard("nav:home", "В меню"),
                source=message,
            )
            return
        data = await state.get_data()
        answers = dict(data.get("agent_application") or {})
        answers["audience"] = value
        await state.update_data(agent_application=answers)
        await self._show_agent_interview_choice(message.from_user.id, "expected_volume", source=message)

    async def lead_name_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        name = (message.text or "").strip()
        if len(name) < 2:
            await self._show_panel(message.from_user.id, self.content.text("errors.invalid_name"), keyboards.simple_back_keyboard("nav:home"), source=message)
            return
        await state.update_data(lead_name=name)
        await state.set_state(LeadStates.phone)
        await self._show_panel(message.from_user.id, self.content.text("screens.lead_phone"), keyboards.simple_back_keyboard("nav:home"), source=message)

    async def lead_phone_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        phone = normalize_phone(message.contact.phone_number if message.contact else message.text)
        if not phone:
            await self._show_panel(message.from_user.id, self.content.text("errors.invalid_phone"), keyboards.simple_back_keyboard("nav:home"), source=message)
            return
        await state.update_data(lead_phone=phone)
        await state.set_state(LeadStates.city)
        await self._show_panel(message.from_user.id, self.content.text("screens.lead_city"), keyboards.simple_back_keyboard("nav:home"), source=message)

    async def lead_city_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if (message.text or "").strip() == "В меню":
            await state.clear()
            await self._open_home(message.from_user.id, message.from_user.username, source=message)
            return
        city = (message.text or "").strip()
        if len(city) < 2:
            await self._show_panel(message.from_user.id, self.content.text("errors.invalid_city"), keyboards.simple_back_keyboard("nav:home"), source=message)
            return
        data = await state.get_data()
        product_id = data.get("product_id") or (self.storage.get_user(message.from_user.id) or {}).get("scenario") or "general"
        self.storage.update_user(message.from_user.id, city=city, scenario=product_id)
        result = self.storage.create_or_update_lead(
            message.from_user.id,
            name=data.get("lead_name", ""),
            phone=data.get("lead_phone", ""),
            city=city,
            contact_time="telegram",
            current_status=(self.storage.get_user(message.from_user.id) or {}).get("status") or "",
            consent_followup=False,
        )
        lead = result["lead"]
        user = self.storage.lead_owner_user(int(lead["id"])) or self.storage.get_user(message.from_user.id) or {}
        started_at = parse_iso(data.get("lead_started_at"))
        form_duration_sec = None
        if started_at:
            form_duration_sec = max(0, int((now_utc() - started_at).total_seconds()))
        context = self.storage.lead_quality_context(int(lead["id"]))
        quality = score_lead(
            form_duration_sec=form_duration_sec,
            duplicate_recent=result["is_duplicate"] or int(context.get("duplicate_phone_count") or 0) > 0,
            recent_user_leads=int(context.get("recent_user_leads") or 0),
            fields_complete=all([data.get("lead_name"), data.get("lead_phone"), city]),
            user_age_sec=context.get("user_age_sec"),
            agent_recent_leads=int(context.get("agent_recent_leads") or 0),
            agent_total_leads=int(context.get("agent_total_leads") or 0),
            agent_rejected_leads=int(context.get("agent_rejected_leads") or 0),
        )
        lead = self.storage.set_lead_quality(
            int(lead["id"]),
            fraud_score=quality.score,
            fraud_status=quality.status,
            reasons=quality.reasons,
            form_duration_sec=form_duration_sec,
        ) or lead
        self.storage.log_event(
            "lead_created",
            user_id=user.get("id"),
            lead_id=lead.get("id"),
            payload={
                "duplicate": result["is_duplicate"],
                "product_id": product_id,
                "fraud_score": quality.score,
                "fraud_status": quality.status,
                "fraud_reasons": quality.reasons,
            },
        )
        if not result["is_duplicate"]:
            integration_results = await self.integrations.send_lead(user, lead)
            external_id = ""
            for item in integration_results:
                body = item.get("body")
                if isinstance(body, dict):
                    external_id = str(body.get("lead_id") or body.get("id") or "")
                if external_id:
                    break
            if any(item.get("ok") for item in integration_results):
                self.storage.mark_lead_synced(int(lead["id"]), external_lead_id=external_id or None)
        if lead.get("agent_id") and quality.auto_block_agent:
            agent = self.storage.set_agent_state(int(lead["agent_id"]), agent_status="banned")
            if agent:
                self.storage.log_event(
                    "agent_auto_blocked",
                    user_id=user.get("id"),
                    lead_id=lead.get("id"),
                    payload={"agent_id": agent["id"], "reason": "quality_threshold"},
                )
                await self._notify_agent_status_change(agent, "banned")
        if quality.status in {"hold", "reject"}:
            await self._notify_admins(
                self._format_risk_alert(lead, quality.score, quality.reasons)
            )
        await state.clear()
        product = self.catalog.get_product(product_id) or {}
        apply_url = self.settings.offer_url or product.get("apply_url") or product.get("official_url") or "https://alfabank.ru/sme/"
        text_key = "screens.lead_duplicate" if result["is_duplicate"] else "screens.lead_saved"
        await self._show_panel(
            message.from_user.id,
            self.content.text(text_key, lead_id=lead.get("id")),
            keyboards.external_link_keyboard("Перейти к оформлению", apply_url),
            source=message,
        )

    async def menu_text_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        await state.clear()
        await self._open_home(message.from_user.id, message.from_user.username, source=message)

    async def fallback_handler(self, message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        if await state.get_state():
            await self._show_panel(message.from_user.id, self.content.text("errors.waiting_for_step"), keyboards.simple_back_keyboard("nav:home"), source=message)
            return
        await self._show_panel(
            message.from_user.id,
            self.content.text("errors.fallback"),
            self._home_keyboard(message.from_user.id, message.from_user.username),
            source=message,
        )

    async def _open_home(self, telegram_id: int, username: str | None, *, source: Message | CallbackQuery) -> None:
        await self._show_screen(
            telegram_id,
            "home",
            self._home_keyboard(telegram_id, username),
            source=source,
        )

    def _home_keyboard(self, telegram_id: int, username: str | None) -> InlineKeyboardMarkup:
        return keyboards.home_keyboard(self._is_admin(telegram_id, username))

    def _help_keyboard(self) -> InlineKeyboardMarkup:
        return keyboards.help_keyboard()

    async def _show_recommendation(
        self,
        telegram_id: int,
        *,
        title: str,
        description: str,
        recommended_ids: list[str],
        next_step: str,
        source: Message | CallbackQuery,
    ) -> None:
        recommended = []
        for product_id in recommended_ids:
            product = self.catalog.get_product(product_id)
            if product:
                recommended.append(f"• {product['title']}")
        await self._show_screen(
            telegram_id,
            "recommendation",
            keyboards.recommendation_keyboard(recommended_ids),
            source=source,
            title=title,
            description=description,
            recommended="\n".join(recommended) or "Подходящие решения не определены.",
            next_step=next_step,
        )

    async def _start_agent_interview(
        self,
        telegram_id: int,
        *,
        source: Message | CallbackQuery,
        state: FSMContext,
    ) -> None:
        agent = self.storage.get_agent_by_user(telegram_id)
        if agent and str(agent.get("agent_status")) in {"draft", "pending", "approved", "banned"}:
            await state.clear()
            await self._show_agent_panel(telegram_id, source=source)
            return
        await state.clear()
        await state.update_data(agent_application={})
        await self._show_agent_interview_choice(telegram_id, "experience", source=source)

    async def _show_agent_interview_choice(
        self,
        telegram_id: int,
        question_key: str,
        *,
        source: Message | CallbackQuery,
    ) -> None:
        question = AGENT_INTERVIEW_QUESTIONS[question_key]
        await self._show_panel(
            telegram_id,
            question["text"].format(step=question["step"], progress=question["progress"]),
            keyboards.agent_interview_choice_keyboard(question_key, question["options"]),
            source=source,
        )

    async def _begin_agent_offer_review(
        self,
        telegram_id: int,
        *,
        state: FSMContext,
        source: Message | CallbackQuery,
    ) -> None:
        data = await state.get_data()
        answers = dict(data.get("agent_application") or {})
        summary = self._format_agent_application_summary(answers)
        agent = self.storage.save_agent_draft_application(telegram_id, answers=answers, summary=summary)
        user = self.storage.get_user(telegram_id) or {}
        self.storage.log_event(
            "agent_application_draft_saved",
            user_id=user.get("id"),
            payload={"agent_id": agent.get("id"), "answers": answers},
        )
        await self._send_agent_offer(telegram_id)
        await state.clear()
        await self._show_panel(
            telegram_id,
            self.content.text("screens.agent_offer_ready"),
            keyboards.agent_offer_confirm_keyboard(),
            source=source,
        )

    async def _start_agent_exam(self, telegram_id: int, *, source: Message | CallbackQuery) -> None:
        agent = self.storage.get_agent_by_user(telegram_id)
        if not agent or str(agent.get("agent_status") or "") != "draft":
            await self._show_agent_panel(telegram_id, source=source)
            return
        if not agent.get("offer_confirmed_at"):
            await self._show_agent_panel(telegram_id, source=source)
            return
        latest_attempt = self.storage.latest_agent_exam_attempt(telegram_id)
        if latest_attempt and int(latest_attempt.get("agent_id") or 0) == int(agent["id"]) and str(latest_attempt.get("status") or "") == "in_progress":
            if await self._expire_agent_exam_if_needed(latest_attempt):
                await self._show_agent_panel(telegram_id, source=source)
                return
            await self._show_agent_exam_question(telegram_id, int(latest_attempt["id"]), source=source)
            return
        blocked_until = parse_iso(agent.get("exam_blocked_until"))
        if blocked_until and blocked_until > now_utc():
            await self._show_agent_panel(telegram_id, source=source)
            return
        seed = f"{telegram_id}:{agent['id']}:{agent.get('exam_attempts') or 0}:{now_utc().isoformat()}"
        attempt = self.storage.create_agent_exam_attempt(
            telegram_id,
            agent_id=int(agent["id"]),
            exam_version=EXAM_VERSION,
            questions=build_exam(seed),
        )
        self.storage.log_event(
            "agent_exam_started",
            user_id=(self.storage.get_user(telegram_id) or {}).get("id"),
            payload={"agent_id": agent["id"], "attempt_id": attempt.get("id")},
        )
        await self._show_agent_exam_question(telegram_id, int(attempt["id"]), source=source)

    async def _expire_agent_exam_if_needed(self, attempt: dict[str, Any]) -> bool:
        if str(attempt.get("status") or "") != "in_progress":
            return False
        started_at = parse_iso(attempt.get("started_at"))
        if not started_at:
            return False
        if now_utc() <= started_at + timedelta(minutes=EXAM_DURATION_MINUTES):
            return False
        await self._finish_agent_exam(int(attempt["id"]), timed_out=True)
        return True

    async def _show_agent_exam_question(
        self,
        telegram_id: int,
        attempt_id: int,
        *,
        source: Message | CallbackQuery,
    ) -> None:
        attempt = self.storage.get_agent_exam_attempt(attempt_id)
        if not attempt:
            await self._show_agent_panel(telegram_id, source=source)
            return
        if await self._expire_agent_exam_if_needed(attempt):
            await self._show_agent_panel(telegram_id, source=source)
            return
        questions = json_loads(attempt.get("questions_json"), [])
        answers = list(json_loads(attempt.get("answers_json"), []))
        current_index = len(answers)
        if current_index >= len(questions):
            await self._finish_agent_exam(attempt_id, source=source)
            return
        question = questions[current_index]
        difficulty_map = {1: "базовый", 2: "средний", 3: "сложный"}
        options_text = "\n".join(
            f"{str(option.get('id') or '').upper()}. {option.get('text') or ''}"
            for option in list(question.get("options") or [])
        )
        await self._show_panel(
            telegram_id,
            self.content.text(
                "screens.agent_exam_question",
                current=current_index + 1,
                total=len(questions),
                progress=progress_bar(current_index, len(questions)),
                difficulty=difficulty_map.get(int(question.get("difficulty") or 1), "базовый"),
                prompt=question.get("prompt") or "",
                options_text=options_text,
                passing_score=PASSING_SCORE,
                duration=EXAM_DURATION_MINUTES,
            ),
            keyboards.agent_exam_question_keyboard(attempt_id, current_index, list(question.get("options") or [])),
            source=source,
        )

    async def _finish_agent_exam(
        self,
        attempt_id: int,
        *,
        source: Message | CallbackQuery | None = None,
        timed_out: bool = False,
    ) -> None:
        attempt = self.storage.get_agent_exam_attempt(attempt_id)
        if not attempt:
            return
        questions = list(json_loads(attempt.get("questions_json"), []))
        answers = list(json_loads(attempt.get("answers_json"), []))
        score = score_exam(questions, answers)
        passed = not timed_out and len(answers) >= len(questions) and score >= PASSING_SCORE
        blocked_until = None if passed else (now_utc() + timedelta(hours=RETRY_COOLDOWN_HOURS)).isoformat()
        updated_attempt = self.storage.finish_agent_exam_attempt(
            attempt_id,
            score=score,
            passed=passed,
            blocked_until=blocked_until,
        ) or attempt
        telegram_id = int(updated_attempt.get("telegram_id") or 0)
        user = self.storage.get_user(telegram_id) or {}
        agent = self.storage.get_agent(int(updated_attempt.get("agent_id") or 0)) if updated_attempt.get("agent_id") else None
        self.storage.log_event(
            "agent_exam_finished",
            user_id=user.get("id"),
            payload={
                "attempt_id": attempt_id,
                "agent_id": (agent or {}).get("id"),
                "score": score,
                "passed": passed,
                "timed_out": timed_out,
            },
        )
        if passed and agent:
            agent = self.storage.activate_agent_application(int(agent["id"])) or agent
            answers_payload = json_loads(agent.get("application_json"), {})
            await self._notify_admins(
                self._format_agent_application_for_admin(agent, answers_payload),
                reply_markup=keyboards.admin_agent_notify_keyboard(int(agent["id"])),
            )
            if source is not None:
                await self._show_panel(
                    telegram_id,
                    self.content.text(
                        "screens.agent_exam_passed",
                        score=score,
                        total=len(questions) or QUESTION_COUNT,
                        passing_score=PASSING_SCORE,
                    ),
                    keyboards.agent_keyboard(approved=False, refresh_callback="agent:panel"),
                    source=source,
                )
            return
        if source is not None:
            retry_at = parse_iso(blocked_until)
            retry_label = retry_at.strftime("%d.%m %H:%M UTC") if retry_at else "-"
            await self._show_panel(
                telegram_id,
                self.content.text(
                    "screens.agent_exam_failed",
                    score=score,
                    total=len(questions) or QUESTION_COUNT,
                    passing_score=PASSING_SCORE,
                    retry_at=retry_label,
                ),
                keyboards.simple_back_keyboard("agent:panel", "К агентскому доступу"),
                source=source,
            )

    async def _show_agent_panel(self, telegram_id: int, *, source: Message | CallbackQuery) -> None:
        agent = self.storage.get_agent_by_user(telegram_id)
        if not agent:
            await self._show_panel(
                telegram_id,
                self.content.text("screens.agent_intro"),
                keyboards.agent_apply_keyboard(),
                source=source,
            )
            return
        deep_link = None
        if self.settings.bot_username and agent.get("referral_code"):
            deep_link = f"https://t.me/{self.settings.bot_username}?start={agent['referral_code']}"
        overview = self.storage.agent_overview(int(agent["id"])) or agent
        status = agent.get("agent_status") or "pending"
        exam_block = ""
        if agent.get("exam_score") is not None and agent.get("exam_total") is not None:
            exam_block = f"\n\n<b>Экзамен</b>\n{int(agent.get('exam_score') or 0)} из {int(agent.get('exam_total') or 0)}"
        summary_block = f"\n\n<b>Анкета</b>\n{escape_html(str(agent.get('application_summary') or '-'))}" if agent.get("application_summary") else ""
        reply_markup: Any = keyboards.agent_keyboard(approved=status == "approved", refresh_callback="agent:panel", deep_link=deep_link)
        if status == "draft":
            blocked_until = parse_iso(agent.get("exam_blocked_until"))
            exam_status = str(agent.get("exam_status") or "not_started")
            if exam_status == "in_progress":
                text = self.content.text("screens.agent_exam_in_progress") + summary_block + exam_block
                reply_markup = keyboards.agent_exam_ready_keyboard(label="Продолжить тест")
            elif exam_status == "failed" and blocked_until and blocked_until > now_utc():
                text = self.content.text(
                    "screens.agent_exam_failed_wait",
                    score=int(agent.get("exam_score") or 0),
                    total=int(agent.get("exam_total") or QUESTION_COUNT),
                    passing_score=PASSING_SCORE,
                    retry_at=blocked_until.strftime("%d.%m %H:%M UTC"),
                ) + summary_block
                reply_markup = keyboards.simple_back_keyboard("agent:panel", "Обновить статус")
            elif exam_status == "failed":
                text = self.content.text(
                    "screens.agent_exam_retry",
                    score=int(agent.get("exam_score") or 0),
                    total=int(agent.get("exam_total") or QUESTION_COUNT),
                    passing_score=PASSING_SCORE,
                ) + summary_block
                reply_markup = keyboards.agent_exam_ready_keyboard(label="Повторить тест")
            elif agent.get("offer_confirmed_at"):
                text = self.content.text(
                    "screens.agent_exam_ready",
                    total=QUESTION_COUNT,
                    passing_score=PASSING_SCORE,
                    duration=EXAM_DURATION_MINUTES,
                ) + summary_block
                reply_markup = keyboards.agent_exam_ready_keyboard(label="Начать тест")
            else:
                text = self.content.text("screens.agent_offer_ready") + summary_block
                reply_markup = keyboards.agent_offer_confirm_keyboard()
        elif status == "pending":
            text = self.content.text("screens.agent_pending") + summary_block + exam_block
        elif status == "approved":
            text = self.content.text(
                "screens.agent_approved",
                referral_code=overview.get("referral_code") or "-",
                deep_link=deep_link or "бот ещё не настроен на deep-link",
                level=agent_level_label(str(overview.get("agent_level") or "junior")),
                payout_value=f"{float(overview.get('payout_value') or 0):.0f}",
                total_leads=int(overview.get("total_leads") or 0),
                good_leads=int(overview.get("good_leads") or 0),
                hold_leads=int(overview.get("hold_leads") or 0),
                reject_leads=int(overview.get("reject_leads") or 0),
                confirmed_leads=int(overview.get("confirmed_leads") or 0),
            ) + exam_block
        elif status == "banned":
            text = self.content.text("screens.agent_banned")
        else:
            text = self.content.text("screens.agent_rejected") + summary_block
        await self._show_panel(
            telegram_id,
            text,
            reply_markup,
            source=source,
        )

    async def _send_agent_offer(self, telegram_id: int) -> None:
        offer_path = self.settings.agent_offer_path
        if not offer_path or not offer_path.exists():
            self.storage.log_event(
                "agent_offer_missing",
                user_id=(self.storage.get_user(telegram_id) or {}).get("id"),
                payload={"path": str(offer_path)},
            )
            return
        try:
            await self.bot.send_document(
                telegram_id,
                FSInputFile(str(offer_path)),
                caption=self.content.text("screens.agent_offer_sent"),
            )
        except Exception as exc:
            self.storage.log_event(
                "agent_offer_send_failed",
                user_id=(self.storage.get_user(telegram_id) or {}).get("id"),
                payload={"path": str(offer_path), "error": str(exc)},
            )

    async def _show_diagnostic_question(
        self,
        telegram_id: int,
        question_key: str,
        *,
        source: Message | CallbackQuery,
    ) -> None:
        question = DIAGNOSTIC_QUESTIONS[question_key]
        await self._show_panel(
            telegram_id,
            question["text"].format(step=question["step"], progress=question.get("progress", "")),
            keyboards.diagnostic_question_keyboard(question_key, question["options"]),
            source=source,
        )

    async def _show_nearby_points(
        self,
        telegram_id: int,
        lat: float,
        lon: float,
        *,
        kind: str,
        source: Message | CallbackQuery,
    ) -> None:
        screen_loading = "atm_loading" if kind == "atm" else "branch_loading"
        screen_result = "atm_result" if kind == "atm" else "branch_result"
        screen_empty = "nearby_empty"
        await self._show_screen(telegram_id, screen_loading, keyboards.simple_back_keyboard("nav:home"), source=source)
        try:
            points = await self.integrations.search_nearby_points(lat, lon, kind=kind)
        except Exception as exc:
            user = self.storage.get_user(telegram_id)
            self.storage.log_event(
                "api_error",
                user_id=(user or {}).get("id"),
                payload={"source": f"nearby_{kind}", "error": str(exc), "lat": lat, "lon": lon},
            )
            points = []
        if not points:
            await self._show_screen(
                telegram_id,
                screen_empty,
                keyboards.nearby_result_keyboard(
                    self.integrations.maps_nearby_url(lat, lon, query=f"Альфа-Банк {NEARBY_KIND_LABELS[kind]}"),
                    self.integrations.maps_nearby_url(lat, lon, query=f"Альфа-Банк {NEARBY_KIND_LABELS[kind]}"),
                    f"maps:{kind}",
                ),
                source=source,
                kind_label=NEARBY_KIND_LABELS[kind],
            )
            return
        lines = []
        for index, point in enumerate(points, start=1):
            lines.append(
                f"{index}. {self._format_distance(point['distance_m'])} — {escape_html(point['title'])}\n"
                f"{escape_html(point['address'])}"
            )
        primary = points[0]
        await self._show_screen(
            telegram_id,
            screen_result,
            keyboards.nearby_result_keyboard(
                self.integrations.maps_route_url(primary.get("lat"), primary.get("lon"), query=primary.get("title", "")),
                self.integrations.maps_nearby_url(lat, lon, query=f"Альфа-Банк {NEARBY_KIND_LABELS[kind]}"),
                f"maps:{kind}",
            ),
            source=source,
            points_text="\n\n".join(lines),
        )

    async def _show_screen(
        self,
        telegram_id: int,
        screen_key: str,
        reply_markup: Any,
        *,
        source: Message | CallbackQuery,
        force_new: bool = False,
        **kwargs: Any,
    ) -> None:
        text = self.content.text(f"screens.{screen_key}", **kwargs)
        if screen_key in {"welcome", "home"} and self._should_show_wake_notice():
            text = f"{self.content.text('screens.wake_notice')}\n\n{text}"
        await self._show_panel(
            telegram_id,
            text,
            reply_markup,
            source=source,
            force_new=force_new,
            media_path=self._media_path(screen_key),
        )

    async def _show_panel(
        self,
        telegram_id: int,
        text: str,
        reply_markup: Any,
        *,
        source: Message | CallbackQuery,
        force_new: bool = False,
        media_path: str | None = None,
    ) -> None:
        if not force_new and isinstance(source, CallbackQuery) and source.message:
            current_panel = {
                "chat_id": source.message.chat.id,
                "message_id": source.message.message_id,
            }
            if await self._try_edit_panel(current_panel["chat_id"], current_panel["message_id"], text, reply_markup, media_path):
                self.storage.save_panel(telegram_id, current_panel["chat_id"], current_panel["message_id"])
                return
            panel = self.storage.get_panel(telegram_id)
            if panel and (
                panel["chat_id"] != current_panel["chat_id"]
                or panel["message_id"] != current_panel["message_id"]
            ):
                if await self._try_edit_panel(panel["chat_id"], panel["message_id"], text, reply_markup, media_path):
                    self.storage.save_panel(telegram_id, panel["chat_id"], panel["message_id"])
                    return
        message = source.message if isinstance(source, CallbackQuery) else source
        if media_path and len(text) <= 1024:
            sent = await message.answer_photo(FSInputFile(media_path), caption=text, reply_markup=reply_markup)
        else:
            sent = await message.answer(text, reply_markup=reply_markup)
        self.storage.save_panel(telegram_id, sent.chat.id, sent.message_id)

    async def _try_edit_panel(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Any,
        media_path: str | None,
    ) -> bool:
        if media_path and len(text) <= 1024:
            try:
                await self.bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=message_id,
                    media=InputMediaPhoto(media=FSInputFile(media_path), caption=text, parse_mode="HTML"),
                    reply_markup=reply_markup,
                )
                return True
            except TelegramBadRequest as exc:
                if self._is_not_modified(exc):
                    return True
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return True
        except TelegramBadRequest as exc:
            if self._is_not_modified(exc):
                return True
        if len(text) <= 1024:
            try:
                await self.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                return True
            except TelegramBadRequest as exc:
                if self._is_not_modified(exc):
                    return True
        return False

    def _media_path(self, screen_key: str) -> str | None:
        payload = self.content.get(f"media.{screen_key}")
        if not payload:
            return None
        if isinstance(payload, str):
            raw = payload
        elif isinstance(payload, dict):
            raw = str(payload.get("path") or "")
        else:
            return None
        if not raw:
            return None
        path = Path(raw)
        if not path.is_absolute():
            path = self.settings.root_dir / raw
        return str(path) if path.exists() else None

    def _is_not_modified(self, exc: TelegramBadRequest) -> bool:
        return "message is not modified" in str(exc).lower()

    def _should_show_wake_notice(self) -> bool:
        return (now_utc() - self.process_started_at) <= timedelta(seconds=120)

    def _format_distance(self, distance_m: int) -> str:
        if distance_m >= 1000:
            return f"{distance_m / 1000:.1f} км"
        return f"{distance_m} м"

    def _diagnostic_answer_label(self, question_key: str, answer_key: str) -> str:
        labels = {
            "payment_method": PAYMENT_LABELS,
            "legal_status": LEGAL_STATUS_LABELS,
            "activity_format": ACTIVITY_LABELS,
        }
        return labels.get(question_key, {}).get(answer_key, answer_key)

    def _build_diagnostic_result(self, diagnostic: dict[str, str]) -> dict[str, Any]:
        payment_method = diagnostic.get("payment_method", "none")
        legal_status = diagnostic.get("legal_status", "none")
        activity_format = diagnostic.get("activity_format", "services")

        if legal_status == "none":
            level = "Оптимизируемый" if payment_method in {"card_transfers", "cash"} else "Базовый"
            readiness_percent = 60 if payment_method in {"card_transfers", "cash"} else 40
            current_state = (
                f"Сейчас оплата идёт как {PAYMENT_LABELS[payment_method]}, а юридический контур ещё не оформлен."
            )
            recommendation = "Начать стоит с регистрации бизнеса и затем перейти к РКО, чтобы собрать рабочий банковский контур."
            why_this = "Регулярные поступления уже есть или скоро появятся, но текущая схема ещё не даёт юридическую базу и расчётный контур."
            recommended_ids = ["registration_business", "rko"]
            next_step = "Сначала откройте регистрацию бизнеса, затем перейдите к РКО."
            primary_product_id = "registration_business"
            secondary_product_id = "rko"
            scenario = "registration_business"
            segment = "just_starting"
            primary_pain = "unclear_status"
        elif legal_status == "self_employed":
            level = "Базовый"
            readiness_percent = 70 if payment_method in {"card_transfers", "cash", "business_account"} else 55
            current_state = (
                f"У вас {LEGAL_STATUS_LABELS[legal_status]}, а расчёты идут как {PAYMENT_LABELS[payment_method]}."
            )
            recommendation = "Если нагрузка растёт и нужны регулярные операции, логичнее перейти к регистрации бизнеса и далее открыть РКО."
            why_this = "Самозанятость подходит для простого старта, но устойчивый рабочий контур обычно требует регистрации бизнеса и отдельного счёта."
            recommended_ids = ["registration_business", "rko"]
            next_step = "Откройте регистрацию бизнеса, затем переходите к РКО."
            primary_product_id = "registration_business"
            secondary_product_id = "rko"
            scenario = "registration_business"
            segment = "self_employed"
            primary_pain = "unclear_status"
        elif payment_method == "business_account":
            level = "Продвинутый"
            readiness_percent = 95
            current_state = (
                f"У вас {LEGAL_STATUS_LABELS[legal_status]}, а платежи уже идут через рабочий контур."
            )
            recommendation = "Фокус можно сместить на задачу бизнеса: офлайн-приём оплаты или обеспечение по контракту."
            why_this = "Юридический и расчётный контур уже есть, поэтому дальше важнее точечный продукт под операционный сценарий."
            recommended_ids = ["trade_acquiring", "guarantees", "rko"]
            next_step = "Откройте продукт под текущую задачу: приём оплат или обеспечение обязательств."
            primary_product_id = "trade_acquiring"
            secondary_product_id = "guarantees"
            scenario = "have_business"
            segment = "have_ip"
            primary_pain = "need_account"
        else:
            level = "Оптимизируемый"
            readiness_percent = 80
            current_state = (
                f"У вас {LEGAL_STATUS_LABELS[legal_status]}, но расчёты пока идут как {PAYMENT_LABELS[payment_method]}."
            )
            recommendation = "Следующий логичный шаг - перевести операционный поток на РКО и затем подключить точечный продукт по задаче."
            why_this = "Статус уже оформлен, но расчёты пока не собраны в рабочий банковский контур. Это создаёт лишнее трение."
            recommended_ids = ["rko"]
            next_step = "Сначала откройте РКО, затем вернитесь к профильному продукту по задаче."
            primary_product_id = "rko"
            secondary_product_id = None
            scenario = "need_account"
            segment = "have_ip"
            primary_pain = "need_account"

        if activity_format == "marketplaces" and "rko" not in recommended_ids:
            recommended_ids.append("rko")
        if activity_format == "mixed" and "guarantees" not in recommended_ids:
            recommended_ids.append("guarantees")
        if activity_format in {"services", "freelance"} and "trade_acquiring" not in recommended_ids:
            recommended_ids.append("trade_acquiring")

        recommended_titles = []
        for product_id in recommended_ids[:3]:
            product = self.catalog.get_product(product_id)
            if product:
                recommended_titles.append(f"• {product['title']}")

        return {
            "level": level,
            "segment_label": SEGMENT_LABELS.get(segment, segment),
            "readiness_percent": readiness_percent,
            "current_state": current_state,
            "recommendation": recommendation,
            "why_this": why_this,
            "recommended_text": "\n".join(recommended_titles) or "Подходящие решения будут доступны в каталоге.",
            "next_step": next_step,
            "primary_product_id": primary_product_id,
            "secondary_product_id": secondary_product_id,
            "scenario": scenario,
            "segment": segment,
            "primary_pain": primary_pain,
            "completed_at": now_utc().isoformat(),
        }

    def _catalog_item(self, product_id: str) -> dict[str, Any]:
        product = self.catalog.get_product(product_id) or {}
        return {"id": product_id, "title": product.get("title", product_id)}

    def _situation_item(self, situation_id: str) -> dict[str, Any]:
        situation = self.catalog.get_situation(situation_id) or {}
        return {"id": situation_id, "title": situation.get("title", situation_id)}

    def _industry_item(self, industry_id: str) -> dict[str, Any]:
        industry = self.catalog.get_industry(industry_id) or {}
        return {"id": industry_id, "title": industry.get("title", industry_id)}

    def _bullets(self, items: list[str]) -> str:
        return "\n".join(f"• {escape_html(item)}" for item in items)

    def _format_admin_leads(self, leads: list[dict[str, Any]], title: str) -> str:
        if not leads:
            return self.content.text("errors.no_leads")
        lines = [f"<b>{escape_html(title)}</b>", ""]
        for lead in leads:
            fraud_label = lead_fraud_status_label(str(lead.get("fraud_status") or "hold"))
            lines.append(
                f"• #{lead['id']} — {escape_html(lead.get('name'))}, {escape_html(LEAD_STATUS_LABELS.get(lead.get('lead_status') or 'new', lead.get('lead_status') or 'new'))}, {escape_html(fraud_label)}"
            )
        return "\n".join(lines)

    def _format_admin_lead(self, lead: dict[str, Any]) -> str:
        reasons = [fraud_reason_label(item) for item in json_loads(lead.get("fraud_reasons_json"), [])]
        reasons_text = ", ".join(reasons) if reasons else "-"
        return (
            f"<b>Лид #{lead['id']}</b>\n"
            f"Имя: {escape_html(lead.get('name'))}\n"
            f"Телефон: {escape_html(lead.get('phone'))}\n"
            f"Город: {escape_html(lead.get('city'))}\n"
            f"Статус: {escape_html(LEAD_STATUS_LABELS.get(lead.get('lead_status') or 'new', lead.get('lead_status') or 'new'))}\n"
            f"Качество: {escape_html(lead_fraud_status_label(str(lead.get('fraud_status') or 'hold')))} ({int(lead.get('fraud_score') or 0)})\n"
            f"Причины: {escape_html(reasons_text)}\n"
            f"Длительность формы: {escape_html((str(lead.get('form_duration_sec')) + ' сек') if lead.get('form_duration_sec') is not None else '-')}\n"
            f"Агент: {escape_html((str(lead.get('agent_id')) + ' / ' + str(lead.get('referral_code') or '-')) if lead.get('agent_id') else '-')}\n"
            f"Сегмент: {escape_html(lead.get('segment') or lead.get('user_segment') or '-')}\n"
            f"Сценарий: {escape_html(lead.get('scenario') or '-')}\n"
            f"Источник: {escape_html(lead.get('source') or '-')}\n"
            f"Кампания: {escape_html(lead.get('campaign') or '-')}\n"
            f"Креатив: {escape_html(lead.get('creative') or '-')}"
        )

    def _format_agent_application_summary(self, answers: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"Опыт: {self._agent_answer_label('experience', answers.get('experience'))}",
                f"Канал: {self._agent_answer_label('traffic_source', answers.get('traffic_source'))}",
                f"Где именно: {answers.get('source_details') or '-'}",
                f"Аудитория: {answers.get('audience') or '-'}",
                f"Объём: {self._agent_answer_label('expected_volume', answers.get('expected_volume'))}",
                f"Правила: {self._agent_answer_label('rules', answers.get('rules'))}",
            ]
        )

    def _format_agent_application_for_admin(self, agent: dict[str, Any], answers: dict[str, Any]) -> str:
        name = agent.get("first_name") or agent.get("full_name") or str(agent.get("telegram_id") or agent.get("id"))
        exam_line = "-"
        if agent.get("exam_score") is not None and agent.get("exam_total") is not None:
            exam_line = f"{int(agent.get('exam_score') or 0)} из {int(agent.get('exam_total') or 0)}"
        return (
            f"<b>Новая анкета агента</b>\n\n"
            f"Агент: #{agent['id']}\n"
            f"Пользователь: {escape_html(name)}\n"
            f"Telegram ID: <code>{agent.get('telegram_id')}</code>\n"
            f"Экзамен: {escape_html(exam_line)}\n\n"
            f"{escape_html(self._format_agent_application_summary(answers))}"
        )

    def _format_admin_agents(self, agents: list[dict[str, Any]], title: str) -> str:
        if not agents:
            return "Пока нет записей."
        lines = [f"<b>{escape_html(title)}</b>", ""]
        for agent in agents:
            name = agent.get("first_name") or agent.get("full_name") or str(agent.get("telegram_id") or agent["id"])
            lines.append(
                f"• #{agent['id']} — {escape_html(name)}, {escape_html(agent_status_label(str(agent.get('agent_status') or 'pending')))}, {escape_html(agent_level_label(str(agent.get('agent_level') or 'junior')))}"
            )
        return "\n".join(lines)

    def _format_admin_agent(self, agent: dict[str, Any]) -> str:
        deep_link = "-"
        if self.settings.bot_username and agent.get("referral_code"):
            deep_link = f"https://t.me/{self.settings.bot_username}?start={agent['referral_code']}"
        total_leads = int(agent.get("total_leads") or 0)
        reject_leads = int(agent.get("reject_leads") or 0)
        reject_ratio = f"{(reject_leads / total_leads * 100):.0f}%" if total_leads else "0%"
        exam_status = str(agent.get("exam_status") or "not_started")
        exam_label = exam_status
        if exam_status == "not_started":
            exam_label = "не запускался"
        elif exam_status == "in_progress":
            exam_label = "идёт"
        elif exam_status == "passed":
            exam_label = "пройден"
        elif exam_status == "failed":
            exam_label = "не пройден"
        blocked_until = parse_iso(agent.get("exam_blocked_until"))
        blocked_text = blocked_until.strftime("%d.%m %H:%M UTC") if blocked_until else "-"
        offer_confirmed_at = parse_iso(agent.get("offer_confirmed_at"))
        offer_confirmed_text = offer_confirmed_at.strftime("%d.%m %H:%M UTC") if offer_confirmed_at else "-"
        return (
            f"<b>Агент #{agent['id']}</b>\n"
            f"Пользователь: {escape_html(agent.get('first_name') or agent.get('full_name') or str(agent.get('telegram_id') or '-'))}\n"
            f"Статус: {escape_html(agent_status_label(str(agent.get('agent_status') or 'pending')))}\n"
            f"Уровень: {escape_html(agent_level_label(str(agent.get('agent_level') or 'junior')))}\n"
            f"Рефкод: <code>{escape_html(agent.get('referral_code') or '-')}</code>\n"
            f"Ссылка: {escape_html(deep_link)}\n"
            f"Модель: {escape_html(str(agent.get('payout_type') or 'revshare'))} {float(agent.get('payout_value') or 0):.0f}%\n"
            f"Лидов: {total_leads}\n"
            f"GOOD/HOLD/REJECT: {int(agent.get('good_leads') or 0)}/{int(agent.get('hold_leads') or 0)}/{reject_leads}\n"
            f"Подтверждено: {int(agent.get('confirmed_leads') or 0)}\n"
            f"Reject ratio: {escape_html(reject_ratio)}\n\n"
            f"<b>Экзамен</b>\n"
            f"Статус: {escape_html(exam_label)}\n"
            f"Баллы: {int(agent.get('exam_score') or 0)} / {int(agent.get('exam_total') or 0)}\n"
            f"Попыток: {int(agent.get('exam_attempts') or 0)}\n"
            f"Повтор после: {escape_html(blocked_text)}\n\n"
            f"<b>Ознакомление с памяткой</b>\n"
            f"Подтверждено: {escape_html(offer_confirmed_text)}\n"
            f"Версия: {escape_html(str(agent.get('offer_document_version') or '-'))}\n\n"
            f"<b>Анкета</b>\n{escape_html(agent.get('application_summary') or 'не заполнена')}"
        )

    def _agent_answer_label(self, question_key: str, answer_key: Any) -> str:
        return AGENT_INTERVIEW_LABELS.get(question_key, {}).get(str(answer_key or ""), str(answer_key or "-"))

    def _format_risk_alert(self, lead: dict[str, Any], score: int, reasons: list[str]) -> str:
        formatted_reasons = ", ".join(fraud_reason_label(item) for item in reasons) or "без пояснений"
        return (
            f"<b>Лид требует проверки</b>\n\n"
            f"Лид: #{lead['id']}\n"
            f"Качество: {lead_fraud_status_label(str(lead.get('fraud_status') or 'hold'))} ({score})\n"
            f"Телефон: {escape_html(lead.get('phone') or '-')}\n"
            f"Причины: {escape_html(formatted_reasons)}"
        )

    async def _notify_admins(self, text: str, reply_markup: Any | None = None) -> None:
        for admin_id in self.settings.admin_ids:
            try:
                await self.bot.send_message(admin_id, text, reply_markup=reply_markup)
            except Exception:
                continue

    async def _notify_agent_status_change(self, agent: dict[str, Any], status: str) -> None:
        telegram_id = agent.get("telegram_id")
        if not telegram_id:
            return
        text_map = {
            "approved": self.content.text("screens.agent_status_approved"),
            "rejected": self.content.text("screens.agent_status_rejected"),
            "banned": self.content.text("screens.agent_status_banned"),
        }
        text = text_map.get(status)
        if not text:
            return
        try:
            await self.bot.send_message(int(telegram_id), text)
        except Exception:
            return

    def _is_admin(self, telegram_id: int, username: str | None) -> bool:
        return self.settings.is_admin(telegram_id, username)
