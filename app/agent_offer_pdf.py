from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

PAGE_SIZE = (1240, 1754)
MARGIN_X = 90
MARGIN_TOP = 110
MARGIN_BOTTOM = 95
LINE_GAP = 12
TITLE_GAP = 26
SECTION_GAP = 18
RED = "#ef3124"
BLACK = "#111111"
GRAY = "#6b7280"
BG = "#ffffff"
FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
DOCUMENT_VERSION = "agent-guide-2026-03-21-v2"


def _load_pil() -> tuple[Any, Any, Any]:
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


def _font(size: int, *, bold: bool = False) -> Any:
    _, _, ImageFont = _load_pil()
    candidates = []
    if bold:
        candidates.extend(
            [
                Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
                Path("/Library/Fonts/Arial Bold.ttf"),
                FONT_REGULAR,
            ]
        )
    else:
        candidates.extend([FONT_REGULAR, Path("/Library/Fonts/Arial Unicode.ttf")])
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _wrap(draw: Any, text: str, font: Any, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _sections() -> list[dict[str, Any]]:
    return [
        {
            "kind": "title",
            "text": "Памятка агента перед доступом к реферальному контуру",
        },
        {
            "kind": "body",
            "text": "Это расширенный справочный документ для кандидата в агентский контур. Он нужен для предварительного ознакомления перед тестом и ручной модерацией. Документ не заменяет полную оферту и не отменяет официальные условия банка.",
        },
        {
            "kind": "body",
            "text": "Задача этого документа - зафиксировать правила доступа, продуктовые рамки, допустимые сценарии и причины отказа. После прочтения бот откроет тест на 20 вопросов. Без прохождения теста заявка администратору не уходит.",
        },
        {
            "kind": "section",
            "text": "1. Что это за контур",
        },
        {
            "kind": "bullet",
            "text": "Бот работает как партнёрский продуктовый навигатор, а не как официальный сервис банка.",
        },
        {
            "kind": "bullet",
            "text": "После одобрения агент получает персональный deeplink на бота, а не отдельный кабинет банка.",
        },
        {
            "kind": "bullet",
            "text": "Финальный переход пользователя идёт по партнёрскому маршруту и на официальную страницу нужного продукта.",
        },
        {
            "kind": "bullet",
            "text": "Внутри маршрута сохраняются события, источник, качество трафика и результаты модерации.",
        },
        {
            "kind": "section",
            "text": "2. Базовый путь пользователя",
        },
        {
            "kind": "bullet",
            "text": "Шаг 1 - пользователь приходит в бот по персональной ссылке агента.",
        },
        {
            "kind": "bullet",
            "text": "Шаг 2 - бот уточняет задачу и показывает короткий продуктовый сценарий.",
        },
        {
            "kind": "bullet",
            "text": "Шаг 3 - пользователь переходит по контролируемому маршруту к официальной странице банка.",
        },
        {
            "kind": "bullet",
            "text": "Шаг 4 - персональные данные запрашиваются только в штатном сценарии и только после согласия.",
        },
        {
            "kind": "body",
            "text": "Агент не должен уводить пользователя в личные сообщения, на собственные формы или на сторонние страницы для ручного сбора контактов. Вся логика допуска и трекинга держится на том, что маршрут остаётся внутри бота до официального перехода.",
        },
        {
            "kind": "page_break",
            "text": "",
        },
        {
            "kind": "section",
            "text": "3. Что обязан соблюдать агент",
        },
        {
            "kind": "bullet",
            "text": "Не выдавать себя за банк, сотрудника банка или официальный банковский сервис.",
        },
        {
            "kind": "bullet",
            "text": "Не обещать одобрение, выпуск продукта, выгоду или гарантированный результат.",
        },
        {
            "kind": "bullet",
            "text": "Не собирать персональные данные в обход согласия и штатного сценария бота.",
        },
        {
            "kind": "bullet",
            "text": "Использовать только согласованные продуктовые сценарии и нейтральный продуктовый тон.",
        },
        {
            "kind": "bullet",
            "text": "Не придумывать собственные условия, тарифы, сроки одобрения и не интерпретировать продукт как уже одобренный.",
        },
        {
            "kind": "bullet",
            "text": "Если пользователь просит точные условия, направлять его на официальный экран продукта или официальный сайт.",
        },
        {
            "kind": "section",
            "text": "4. Что запрещено",
        },
        {
            "kind": "bullet",
            "text": "Спам, мотивированный трафик, роботизированные обзвоны, popup, popunder и clickunder.",
        },
        {
            "kind": "bullet",
            "text": "Брендовый контекст, мимикрия под бренд, фейковые публичные страницы и группы, оформленные как банк.",
        },
        {
            "kind": "bullet",
            "text": "Сторонние формы и лендинги, где агент сам собирает лиды без корректного согласия и контролируемого маршрута.",
        },
        {
            "kind": "section",
            "text": "5. Тон и подача",
        },
        {
            "kind": "bullet",
            "text": "Подача должна быть короткой, спокойной и продуктовой. Без крика, давления и маркетинговых обещаний.",
        },
        {
            "kind": "bullet",
            "text": "Бот не продаёт продукт в лоб. Он создаёт ощущение, что продукт - логичный итог понятного сценария.",
        },
        {
            "kind": "bullet",
            "text": "Нельзя использовать сленг, грубые обещания и формулировки в стиле агрессивного арбитража.",
        },
        {
            "kind": "body",
            "text": "Корректная подача - это партнёрский сервис с банковской логикой интерфейса: понятные шаги, короткие результаты, раскрытие статуса сервиса и переход на официальные условия.",
        },
        {
            "kind": "page_break",
            "text": "",
        },
        {
            "kind": "section",
            "text": "6. Продукты текущего контура",
        },
        {
            "kind": "bullet",
            "text": "РКО - базовый рабочий контур для расчётов бизнеса и разделения личных и деловых операций.",
        },
        {
            "kind": "bullet",
            "text": "Регистрация бизнеса - стартовый сценарий, если уже есть активность, но юридический статус ещё не оформлен.",
        },
        {
            "kind": "bullet",
            "text": "Торговый эквайринг - сценарий для офлайн-точек и приёма оплаты картой на месте продаж.",
        },
        {
            "kind": "bullet",
            "text": "Банковская гарантия - инструмент под обеспечение обязательств, контрактов и тендерных требований.",
        },
        {
            "kind": "section",
            "text": "7. Как подбирать продукт по ситуации",
        },
        {
            "kind": "bullet",
            "text": "Если у клиента уже есть ИП или ООО и нужны расчёты с контрагентами, базовый фокус - РКО.",
        },
        {
            "kind": "bullet",
            "text": "Если продажи уже есть, но статус не оформлен, сначала показывается регистрация бизнеса, затем РКО как следующий рабочий шаг.",
        },
        {
            "kind": "bullet",
            "text": "Если у клиента офлайн-точка или кассовый поток на месте, сначала уместен торговый эквайринг.",
        },
        {
            "kind": "bullet",
            "text": "Если нужен инструмент обеспечения для сделки или тендера, логичный продукт - банковская гарантия.",
        },
        {
            "kind": "section",
            "text": "8. Геопоиск и адреса",
        },
        {
            "kind": "bullet",
            "text": "Геолокация в Telegram может работать неточно при VPN или прокси.",
        },
        {
            "kind": "bullet",
            "text": "В таком случае бот должен предлагать ручной ввод города или адреса как основной точный сценарий.",
        },
        {
            "kind": "bullet",
            "text": "Результат геопоиска - это точки рядом, открытие карты и маршрут, а не длинная консультация.",
        },
        {
            "kind": "body",
            "text": "Если адрес не распознан автоматически, допустим fallback на поиск в Яндекс Картах. Недопустимо подставлять случайный адрес или скрывать проблему точности.",
        },
        {
            "kind": "page_break",
            "text": "",
        },
        {
            "kind": "section",
            "text": "9. Как выдаётся доступ",
        },
        {
            "kind": "bullet",
            "text": "Сначала агент проходит собеседование внутри бота.",
        },
        {
            "kind": "bullet",
            "text": "Потом подтверждает ознакомление с этим документом.",
        },
        {
            "kind": "bullet",
            "text": "После этого открывается экзамен на знание правил и продуктовой логики.",
        },
        {
            "kind": "bullet",
            "text": "Если балл ниже порога, анкета не уходит администратору и доступ не открывается.",
        },
        {
            "kind": "bullet",
            "text": "Если балл достаточный, анкета попадает админу на ручную модерацию.",
        },
        {
            "kind": "section",
            "text": "10. Почему заявка может не дойти до администратора",
        },
        {
            "kind": "bullet",
            "text": "Не подтверждены правила работы с трафиком и позиционированием.",
        },
        {
            "kind": "bullet",
            "text": "Не подтверждено ознакомление с памяткой.",
        },
        {
            "kind": "bullet",
            "text": "Тест не пройден по проходному баллу или попытка завершилась по таймауту.",
        },
        {
            "kind": "bullet",
            "text": "Анкета противоречит правилам: запрещённые каналы, мимикрия под бренд или ручной серый сбор лидов.",
        },
        {
            "kind": "bullet",
            "text": "Источник трафика описан слишком размыто и не проходит базовую проверку.",
        },
        {
            "kind": "section",
            "text": "11. Что видит администратор",
        },
        {
            "kind": "bullet",
            "text": "Анкету кандидата, канал трафика, описание аудитории, ожидаемый объём и подтверждение правил.",
        },
        {
            "kind": "bullet",
            "text": "Статус экзамена, число попыток, результат и дату последней попытки.",
        },
        {
            "kind": "bullet",
            "text": "Источники трафика, качество лидов, GOOD / HOLD / REJECT и поведение по антифроду.",
        },
        {
            "kind": "body",
            "text": "Ручная модерация нужна не для усложнения доступа, а для контроля качества, соответствия оферте и устойчивости всего контура.",
        },
        {
            "kind": "page_break",
            "text": "",
        },
        {
            "kind": "section",
            "text": "12. Финальный чек-лист агента",
        },
        {
            "kind": "bullet",
            "text": "Я понимаю, что сервис партнёрский и не называю его официальным сервисом банка.",
        },
        {
            "kind": "bullet",
            "text": "Я использую только допустимые сценарии трафика и не запускаю спам или мотивированный трафик.",
        },
        {
            "kind": "bullet",
            "text": "Я не обещаю одобрение, выпуск продукта или фиксированный результат.",
        },
        {
            "kind": "bullet",
            "text": "Я не собираю персональные данные вручную вне контролируемого сценария.",
        },
        {
            "kind": "bullet",
            "text": "Я понимаю текущий каталог: РКО, регистрация бизнеса, торговый эквайринг, банковская гарантия.",
        },
        {
            "kind": "bullet",
            "text": "Я понимаю, когда нужен ручной адрес вместо неточной Telegram-геолокации.",
        },
        {
            "kind": "bullet",
            "text": "Я понимаю, что до админа доходит только успешно пройденная анкета.",
        },
        {
            "kind": "section",
            "text": "13. Что дальше",
        },
        {
            "kind": "body",
            "text": "После этого документа бот попросит подтвердить ознакомление и откроет тест из 20 вопросов. Проходной балл высокий, потому что доступ выдаётся не всем, а только тем, кто действительно понимает рамки продукта, правила трафика и допустимую коммуникацию.",
        },
        {
            "kind": "body",
            "text": "Если тест пройден, анкета уходит администратору. После ручного одобрения бот создаёт персональный код и отдельную ссылку для вашего аккаунта.",
        },
        {
            "kind": "footnote",
            "text": "Справочная версия для внутреннего допуска. Версия документа фиксируется ботом и привязывается к подтверждению ознакомления перед тестом.",
        },
    ]


def _render_pages() -> list[Any]:
    Image, ImageDraw, _ = _load_pil()
    title_font = _font(54, bold=True)
    section_font = _font(30, bold=True)
    body_font = _font(24)
    note_font = _font(20)
    images: list[Any] = []

    def new_page() -> tuple[Any, Any, int]:
        image = Image.new("RGB", PAGE_SIZE, BG)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, PAGE_SIZE[0], 22), fill=RED)
        draw.text((MARGIN_X, 44), "Партнёрский агентский контур", font=note_font, fill=RED)
        return image, draw, MARGIN_TOP

    image, draw, y = new_page()
    max_width = PAGE_SIZE[0] - 2 * MARGIN_X

    for block in _sections():
        kind = str(block["kind"])
        text = str(block["text"])
        if kind == "page_break":
            images.append(image)
            image, draw, y = new_page()
            continue
        if kind == "title":
            lines = _wrap(draw, text, title_font, max_width)
            height = len(lines) * 64 + TITLE_GAP
            if y + height > PAGE_SIZE[1] - MARGIN_BOTTOM:
                images.append(image)
                image, draw, y = new_page()
            for line in lines:
                draw.text((MARGIN_X, y), line, font=title_font, fill=BLACK)
                y += 64
            y += TITLE_GAP
            continue

        if kind == "section":
            lines = _wrap(draw, text, section_font, max_width)
            height = len(lines) * 38 + SECTION_GAP
            if y + height > PAGE_SIZE[1] - MARGIN_BOTTOM:
                images.append(image)
                image, draw, y = new_page()
            for line in lines:
                draw.text((MARGIN_X, y), line, font=section_font, fill=RED)
                y += 38
            y += SECTION_GAP
            continue

        font = note_font if kind == "footnote" else body_font
        fill = GRAY if kind == "footnote" else BLACK
        prefix = "• " if kind == "bullet" else ""
        block_indent = 36 if kind == "bullet" else 0
        wrap_width = max_width - block_indent
        lines = _wrap(draw, text, font, wrap_width)
        line_height = 32 if kind == "footnote" else 34
        height = len(lines) * line_height + LINE_GAP
        if y + height > PAGE_SIZE[1] - MARGIN_BOTTOM:
            images.append(image)
            image, draw, y = new_page()
        for index, line in enumerate(lines):
            content = f"{prefix}{line}" if index == 0 and prefix else line
            x = MARGIN_X + block_indent
            if index > 0 and prefix:
                x += 20
            draw.text((x, y), content, font=font, fill=fill)
            y += line_height
        y += LINE_GAP

    images.append(image)
    total_pages = len(images)
    footer_font = _font(18)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    for index, page in enumerate(images, start=1):
        draw = ImageDraw.Draw(page)
        footer = f"Страница {index} из {total_pages}  •  {generated_at}"
        width = draw.textlength(footer, font=footer_font)
        draw.text((PAGE_SIZE[0] - MARGIN_X - width, PAGE_SIZE[1] - 48), footer, font=footer_font, fill=GRAY)
    return images


def ensure_agent_offer_pdf(path: str | Path) -> Path:
    target = Path(path)
    version_path = target.with_suffix(f"{target.suffix}.version")
    if (
        target.exists()
        and target.stat().st_size > 0
        and version_path.exists()
        and version_path.read_text(encoding="utf-8").strip() == DOCUMENT_VERSION
    ):
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    pages = _render_pages()
    rgb_pages = [page.convert("RGB") for page in pages]
    rgb_pages[0].save(
        target,
        "PDF",
        resolution=150.0,
        save_all=True,
        append_images=rgb_pages[1:],
    )
    version_path.write_text(DOCUMENT_VERSION, encoding="utf-8")
    return target
