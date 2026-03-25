from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def _inline(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def home_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Подобрать", callback_data="diagnostic:start"),
            InlineKeyboardButton(text="Каталог", callback_data="catalog:page:0"),
        ],
        [
            InlineKeyboardButton(text="Рядом", callback_data="maps:open"),
            InlineKeyboardButton(text="Курс", callback_data="currency:open"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Админ-панель", callback_data="admin:panel")])
    return _inline(rows)


def catalog_keyboard(items: list[dict[str, Any]], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=item["title"], callback_data=f"product:open:{item['id']}")] for item in items]
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="Назад", callback_data=f"catalog:page:{page - 1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="Ещё", callback_data=f"catalog:page:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def picker_keyboard(items: list[dict[str, Any]], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=item["title"], callback_data=f"picker:select:{item['id']}")] for item in items]
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="Назад", callback_data=f"picker:page:{page - 1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="Ещё", callback_data=f"picker:page:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def industries_keyboard(items: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=item["title"], callback_data=f"industry:open:{item['id']}")] for item in items]
    rows.append([InlineKeyboardButton(text="К подбору", callback_data="picker:page:0")])
    return _inline(rows)


def product_keyboard(
    product_id: str,
    primary_url: str,
    official_url: str | None = None,
    *,
    extra_callback: str | None = None,
    extra_label: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Перейти к оформлению", url=primary_url)]]
    if official_url:
        rows.append([InlineKeyboardButton(text="Узнать больше", url=official_url)])
    if extra_callback and extra_label:
        rows.append([InlineKeyboardButton(text=extra_label, callback_data=extra_callback)])
    rows.append([InlineKeyboardButton(text="К каталогу", callback_data="catalog:page:0")])
    return _inline(rows)


def recommendation_keyboard(product_ids: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Открыть решение", callback_data=f"product:open:{product_id}")] for product_id in product_ids[:3]]
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def maps_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Указать адрес или город", callback_data="maps:address")],
            [InlineKeyboardButton(text="Банкоматы рядом", callback_data="maps:atm")],
            [InlineKeyboardButton(text="Отделения рядом", callback_data="maps:branch")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def maps_result_keyboard(map_url: str, extra_url: str | None = None, extra_label: str = "Открыть карту") -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Открыть в Яндекс Картах", url=map_url)]]
    if extra_url:
        rows.append([InlineKeyboardButton(text=extra_label, url=extra_url)])
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def external_link_keyboard(primary_label: str, primary_url: str, secondary_label: str | None = None, secondary_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=primary_label, url=primary_url)]]
    if secondary_label and secondary_url:
        rows.append([InlineKeyboardButton(text=secondary_label, url=secondary_url)])
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def currency_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Обновить курс", callback_data="currency:refresh")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def diagnostic_start_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Начать", callback_data="diagnostic:start")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def diagnostic_question_keyboard(question_key: str, options: list[dict[str, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=option["title"], callback_data=f"diagnostic:answer:{question_key}:{option['id']}")] for option in options]
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def diagnostic_result_keyboard(primary_product_id: str, secondary_product_id: str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="Подробнее по решению", callback_data=f"product:open:{primary_product_id}")]]
    if secondary_product_id:
        rows.append([InlineKeyboardButton(text="Открыть дополнительный продукт", callback_data=f"product:open:{secondary_product_id}")])
    rows.append([InlineKeyboardButton(text="Пройти ещё раз", callback_data="diagnostic:start")])
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def nearby_result_keyboard(primary_url: str, map_url: str, retry_callback: str) -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Открыть маршрут", url=primary_url)],
            [InlineKeyboardButton(text="Открыть карту", url=map_url)],
            [InlineKeyboardButton(text="Обновить поиск", callback_data=retry_callback)],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def location_request_keyboard(label: str = "📍 Отправить геопозицию") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label, request_location=True)],
            [KeyboardButton(text="В меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def tariff_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Только старт", callback_data="tariff:starter")],
            [InlineKeyboardButton(text="Базовые расчёты", callback_data="tariff:simple")],
            [InlineKeyboardButton(text="Есть рост", callback_data="tariff:growth")],
            [InlineKeyboardButton(text="Много платежей", callback_data="tariff:active")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def applications_keyboard(show_new: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if show_new:
        rows.append([InlineKeyboardButton(text="Новая заявка", callback_data="lead:start:general")])
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def simple_back_keyboard(callback_data: str = "nav:home", label: str = "Главный экран") -> InlineKeyboardMarkup:
    return _inline([[InlineKeyboardButton(text=label, callback_data=callback_data)]])


def help_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Как это работает", callback_data="info:work")],
        [InlineKeyboardButton(text="Правовой режим", callback_data="info:legal")],
        [InlineKeyboardButton(text="Чеклист ИП", callback_data="info:ip_checklist")],
        [InlineKeyboardButton(text="Самозанятый или ИП", callback_data="info:compare")],
        [InlineKeyboardButton(text="Сроки и ошибки", callback_data="info:timeline")],
        [InlineKeyboardButton(text="Агентский доступ", callback_data="agent:panel")],
        [InlineKeyboardButton(text="Каталог", callback_data="catalog:page:0")],
    ]
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def consent_keyboard(product_id: str) -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Согласен продолжить", callback_data=f"lead:consent:{product_id}:yes")],
            [InlineKeyboardButton(text="Не сейчас", callback_data=f"lead:consent:{product_id}:no")],
        ]
    )


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить номер", request_contact=True)],
            [KeyboardButton(text="В меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def admin_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [
                InlineKeyboardButton(text="Пользователи", callback_data="admin:users"),
                InlineKeyboardButton(text="Активность", callback_data="admin:activity"),
            ],
            [
                InlineKeyboardButton(text="Новые", callback_data="admin:leads:new"),
                InlineKeyboardButton(text="Активные", callback_data="admin:leads:active"),
            ],
            [
                InlineKeyboardButton(text="В обработке", callback_data="admin:leads:in_review"),
                InlineKeyboardButton(text="Подтверждён", callback_data="admin:leads:confirmed"),
            ],
            [
                InlineKeyboardButton(text="Потерян", callback_data="admin:leads:lost"),
                InlineKeyboardButton(text="Сводка", callback_data="admin:funnel"),
            ],
            [
                InlineKeyboardButton(text="Источники", callback_data="admin:sources"),
                InlineKeyboardButton(text="Этапы", callback_data="admin:dropoff"),
            ],
            [
                InlineKeyboardButton(text="Качество", callback_data="admin:quality"),
                InlineKeyboardButton(text="HOLD", callback_data="admin:fraud:hold"),
            ],
            [
                InlineKeyboardButton(text="REJECT", callback_data="admin:fraud:reject"),
                InlineKeyboardButton(text="GOOD", callback_data="admin:fraud:good"),
            ],
            [
                InlineKeyboardButton(text="Агенты", callback_data="admin:agents:approved"),
                InlineKeyboardButton(text="Запросы агентов", callback_data="admin:agents:pending"),
            ],
            [InlineKeyboardButton(text="Черновики агентов", callback_data="admin:agents:draft")],
            [
                InlineKeyboardButton(text="Ошибки API", callback_data="admin:api"),
                InlineKeyboardButton(text="CSV", callback_data="admin:csv"),
            ],
            [InlineKeyboardButton(text="CSV агентов", callback_data="admin:csv_agents")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def admin_lead_keyboard(lead_id: int) -> InlineKeyboardMarkup:
    return _inline(
        [
            [
                InlineKeyboardButton(text="Активный", callback_data=f"admin:set:{lead_id}:active"),
                InlineKeyboardButton(text="Заинтересован", callback_data=f"admin:set:{lead_id}:interested"),
            ],
            [
                InlineKeyboardButton(text="Отправил заявку", callback_data=f"admin:set:{lead_id}:submitted"),
                InlineKeyboardButton(text="В обработке", callback_data=f"admin:set:{lead_id}:in_review"),
            ],
            [
                InlineKeyboardButton(text="Подтверждён", callback_data=f"admin:set:{lead_id}:confirmed"),
                InlineKeyboardButton(text="Потерян", callback_data=f"admin:set:{lead_id}:lost"),
            ],
            [
                InlineKeyboardButton(text="GOOD", callback_data=f"admin:fraudset:{lead_id}:good"),
                InlineKeyboardButton(text="HOLD", callback_data=f"admin:fraudset:{lead_id}:hold"),
            ],
            [InlineKeyboardButton(text="REJECT", callback_data=f"admin:fraudset:{lead_id}:reject")],
            [InlineKeyboardButton(text="Повторный контакт", callback_data=f"admin:set:{lead_id}:recontact")],
            [InlineKeyboardButton(text="К панели", callback_data="admin:panel")],
        ]
    )


def admin_list_keyboard(leads: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for lead in leads[:5]:
        lead_id = int(lead["id"])
        label = f"#{lead_id} {str(lead.get('name') or 'Лид')[:18]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"admin:open:{lead_id}")])
    rows.append([InlineKeyboardButton(text="К панели", callback_data="admin:panel")])
    return _inline(rows)


def agent_keyboard(*, approved: bool, refresh_callback: str, deep_link: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if approved and deep_link:
        rows.append([InlineKeyboardButton(text="Открыть свою ссылку", url=deep_link)])
    rows.append([InlineKeyboardButton(text="Обновить статус", callback_data=refresh_callback)])
    rows.append([InlineKeyboardButton(text="Главный экран", callback_data="nav:home")])
    return _inline(rows)


def agent_apply_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Пройти собеседование", callback_data="agent:apply")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def agent_offer_confirm_keyboard() -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Прочитал памятку - открыть тест", callback_data="agent:confirm_read")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def agent_exam_ready_keyboard(*, label: str = "Начать тест") -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text=label, callback_data="agent:exam_start")],
            [InlineKeyboardButton(text="Главный экран", callback_data="nav:home")],
        ]
    )


def agent_exam_question_keyboard(attempt_id: int, question_index: int, options: list[dict[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=option["id"].upper(), callback_data=f"agentexam:answer:{attempt_id}:{question_index}:{option['id']}")]
        for option in options
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="nav:home")])
    return _inline(rows)


def agent_interview_choice_keyboard(question_key: str, options: list[dict[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=option["title"], callback_data=f"agentq:{question_key}:{option['id']}")]
        for option in options
    ]
    rows.append([InlineKeyboardButton(text="В меню", callback_data="nav:home")])
    return _inline(rows)


def admin_agent_notify_keyboard(agent_id: int) -> InlineKeyboardMarkup:
    return _inline(
        [
            [InlineKeyboardButton(text="Открыть анкету", callback_data=f"admin:agent_open:{agent_id}")],
            [InlineKeyboardButton(text="К панели", callback_data="admin:panel")],
        ]
    )


def admin_agent_list_keyboard(agents: list[dict[str, Any]], *, back_callback: str = "admin:panel") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for agent in agents[:8]:
        label = f"#{agent['id']} {str(agent.get('first_name') or agent.get('full_name') or agent.get('telegram_id'))[:18]}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"admin:agent_open:{agent['id']}")])
    rows.append([InlineKeyboardButton(text="К панели", callback_data=back_callback)])
    return _inline(rows)


def admin_agent_keyboard(agent_id: int) -> InlineKeyboardMarkup:
    return _inline(
        [
            [
                InlineKeyboardButton(text="Одобрить", callback_data=f"admin:agent_set:{agent_id}:approved"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"admin:agent_set:{agent_id}:rejected"),
            ],
            [
                InlineKeyboardButton(text="Junior", callback_data=f"admin:agent_level:{agent_id}:junior"),
                InlineKeyboardButton(text="Pro", callback_data=f"admin:agent_level:{agent_id}:pro"),
            ],
            [
                InlineKeyboardButton(text="Elite", callback_data=f"admin:agent_level:{agent_id}:elite"),
                InlineKeyboardButton(text="Блок", callback_data=f"admin:agent_set:{agent_id}:banned"),
            ],
            [InlineKeyboardButton(text="К агентам", callback_data="admin:agents:approved")],
        ]
    )
