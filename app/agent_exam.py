from __future__ import annotations

import random
from typing import Any


QUESTION_COUNT = 20
PASSING_SCORE = 18
EXAM_DURATION_MINUTES = 12
RETRY_COOLDOWN_HOURS = 12
EXAM_VERSION = "agent-rules-2026-03-21"


QUESTION_POOL: list[dict[str, Any]] = [
    {
        "id": "partner_status",
        "difficulty": 1,
        "prompt": "Как правильно представлять бот пользователю?",
        "options": [
            {"text": "Как официальный бот банка", "correct": False},
            {"text": "Как партнёрский сервис с переходом на официальный сайт банка", "correct": True},
            {"text": "Как личный чат менеджера банка", "correct": False},
            {"text": "Как независимый сервис, который сам принимает решения банка", "correct": False},
        ],
    },
    {
        "id": "consent_before_pii",
        "difficulty": 1,
        "prompt": "Когда можно запрашивать у пользователя персональные данные для заявки?",
        "options": [
            {"text": "Сразу после /start", "correct": False},
            {"text": "После явного согласия на передачу и обработку данных", "correct": True},
            {"text": "После первого клика по каталогу", "correct": False},
            {"text": "В любой момент, если человек заинтересован", "correct": False},
        ],
    },
    {
        "id": "promise_approval",
        "difficulty": 1,
        "prompt": "Можно ли обещать одобрение продукта или гарантированный результат?",
        "options": [
            {"text": "Да, если это повышает конверсию", "correct": False},
            {"text": "Да, если клиент сам просит гарантию", "correct": False},
            {"text": "Нет, обещать одобрение или результат нельзя", "correct": True},
            {"text": "Можно только в личной переписке", "correct": False},
        ],
    },
    {
        "id": "spam_rule",
        "difficulty": 1,
        "prompt": "Какой способ привлечения нарушает правила?",
        "options": [
            {"text": "Контентный пост с переходом в бот", "correct": False},
            {"text": "Подборка полезных материалов с deeplink в бот", "correct": False},
            {"text": "Спам-рассылка без согласия и мотивированный трафик", "correct": True},
            {"text": "Личный канал с собственным контентом", "correct": False},
        ],
    },
    {
        "id": "agent_link_type",
        "difficulty": 1,
        "prompt": "Какую ссылку получает одобренный агент?",
        "options": [
            {"text": "Персональный deeplink на бота", "correct": True},
            {"text": "Новый официальный домен банка", "correct": False},
            {"text": "Отдельный кабинет банка с правами менеджера", "correct": False},
            {"text": "Ссылку на внешний сборщик лидов", "correct": False},
        ],
    },
    {
        "id": "final_cta_link",
        "difficulty": 1,
        "prompt": "Куда должен вести финальный CTA после подбора продукта?",
        "options": [
            {"text": "На мастер-партнёрскую ссылку и официальную страницу продукта", "correct": True},
            {"text": "На личный Telegram агента", "correct": False},
            {"text": "На стороннюю форму без домена банка", "correct": False},
            {"text": "На случайный лендинг для теста креативов", "correct": False},
        ],
    },
    {
        "id": "popup_forbidden",
        "difficulty": 1,
        "prompt": "Какой рекламный формат прямо нежелателен и должен считаться запрещённым в агентской работе?",
        "options": [
            {"text": "Popup, popunder и clickunder", "correct": True},
            {"text": "Контентный обзор", "correct": False},
            {"text": "Небрендовый пост в Telegram", "correct": False},
            {"text": "Объясняющая статья на сайте", "correct": False},
        ],
    },
    {
        "id": "products_scope",
        "difficulty": 1,
        "prompt": "Какие продукты сейчас входят в продуктовый контур этого бота?",
        "options": [
            {"text": "РКО, регистрация бизнеса, торговый эквайринг, банковская гарантия", "correct": True},
            {"text": "Карты, ипотека, инвестиции, вклады", "correct": False},
            {"text": "Любые продукты банка без ограничений", "correct": False},
            {"text": "Только кредиты наличными", "correct": False},
        ],
    },
    {
        "id": "brand_context",
        "difficulty": 2,
        "prompt": "Какой трафик нужно считать рискованным и не использовать без отдельного разрешения?",
        "options": [
            {"text": "Небрендовый контекст по бизнес-задачам", "correct": False},
            {"text": "Пост с разбором сценариев бизнеса", "correct": False},
            {"text": "Брендовый контекст с названием банка в ставках и объявлениях", "correct": True},
            {"text": "Материал на собственном сайте о выборе продукта", "correct": False},
        ],
    },
    {
        "id": "mimicry",
        "difficulty": 2,
        "prompt": "Что считается недопустимой мимикрией под бренд?",
        "options": [
            {"text": "Ссылка на официальный сайт продукта", "correct": False},
            {"text": "Публичный канал или страница, оформленные как официальный сервис банка", "correct": True},
            {"text": "Нейтральный навигатор с партнёрским раскрытием", "correct": False},
            {"text": "Карточка продукта внутри бота с дисклеймером", "correct": False},
        ],
    },
    {
        "id": "official_rates",
        "difficulty": 2,
        "prompt": "Пользователь просит точные тарифы и условия. Что корректно?",
        "options": [
            {"text": "Назвать тарифы по памяти и не давать ссылку", "correct": False},
            {"text": "Отправить на официальный продуктовый экран или страницу банка", "correct": True},
            {"text": "Сказать, что условия не важны до заявки", "correct": False},
            {"text": "Передать вопрос другому агенту в личку", "correct": False},
        ],
    },
    {
        "id": "manual_address",
        "difficulty": 2,
        "prompt": "Если геопозиция в Telegram определяется неточно из-за VPN или прокси, что должен предложить бот?",
        "options": [
            {"text": "Принудительно повторять запрос геолокации", "correct": False},
            {"text": "Ручной ввод города или адреса", "correct": True},
            {"text": "Случайно выбирать ближайший город", "correct": False},
            {"text": "Игнорировать раздел геопоиска", "correct": False},
        ],
    },
    {
        "id": "admin_gate",
        "difficulty": 2,
        "prompt": "Когда заявка на агентский доступ может уйти админу?",
        "options": [
            {"text": "Сразу после нажатия на кнопку агентского доступа", "correct": False},
            {"text": "После анкеты, ознакомления с документом и успешной сдачи экзамена", "correct": True},
            {"text": "После первого перехода агента по своей ссылке", "correct": False},
            {"text": "Только после ручного сообщения администратору", "correct": False},
        ],
    },
    {
        "id": "data_outside_bot",
        "difficulty": 2,
        "prompt": "Можно ли агенту собирать телефоны и анкеты вне бота, а потом вручную передавать их как лиды?",
        "options": [
            {"text": "Да, если человек не против на словах", "correct": False},
            {"text": "Да, если источник трафика дорогой", "correct": False},
            {"text": "Нет, персональные данные нельзя уводить в серый ручной сбор без корректного согласия", "correct": True},
            {"text": "Можно, если это делает помощник агента", "correct": False},
        ],
    },
    {
        "id": "traffic_change",
        "difficulty": 2,
        "prompt": "Агент сменил канал трафика после одобрения. Что корректно?",
        "options": [
            {"text": "Ничего не менять, пока есть лиды", "correct": False},
            {"text": "Зафиксировать новый канал и при необходимости обновить модерацию", "correct": True},
            {"text": "Скрыть источник, чтобы не снижать конверсию", "correct": False},
            {"text": "Вести оба канала без логирования", "correct": False},
        ],
    },
    {
        "id": "quality_control",
        "difficulty": 2,
        "prompt": "Что происходит с агентом при системно плохом качестве и высоком reject ratio?",
        "options": [
            {"text": "Ничего, если объём высокий", "correct": False},
            {"text": "Качество игнорируется до выплаты", "correct": False},
            {"text": "Агент может быть ограничен или заблокирован по антифроду", "correct": True},
            {"text": "Ему автоматически повышают ставку", "correct": False},
        ],
    },
    {
        "id": "official_tone",
        "difficulty": 2,
        "prompt": "Какой тон соответствует банковскому интерфейсу?",
        "options": [
            {"text": "Давление, обещания и крикливые CTA", "correct": False},
            {"text": "Короткий, нейтральный и предсказуемый продуктовый тон", "correct": True},
            {"text": "Максимально разговорный стиль и сленг", "correct": False},
            {"text": "Сверхэмоциональная мотивация ради конверсии", "correct": False},
        ],
    },
    {
        "id": "readiness_flow",
        "difficulty": 2,
        "prompt": "Что создаёт ощущение системности в банковском боте?",
        "options": [
            {"text": "Несколько случайных веток и много CTA одновременно", "correct": False},
            {"text": "Шаги, прогресс и понятный следующий результат", "correct": True},
            {"text": "Минимум структуры, максимум свободного чата", "correct": False},
            {"text": "Постоянный сбор контактов в каждом разделе", "correct": False},
        ],
    },
    {
        "id": "scenario_offline_store",
        "difficulty": 3,
        "prompt": "Клиент открывает офлайн-точку и хочет принимать оплату картой на месте. Какой продукт самый уместный первым?",
        "options": [
            {"text": "Банковская гарантия", "correct": False},
            {"text": "Торговый эквайринг", "correct": True},
            {"text": "Регистрация бизнеса только без других шагов", "correct": False},
            {"text": "Любой продукт подойдёт одинаково", "correct": False},
        ],
    },
    {
        "id": "scenario_contract_security",
        "difficulty": 3,
        "prompt": "Клиенту нужно обеспечение по контракту или тендеру. Что подходит по смыслу продукта?",
        "options": [
            {"text": "Торговый эквайринг", "correct": False},
            {"text": "РКО без дополнительных инструментов", "correct": False},
            {"text": "Банковская гарантия", "correct": True},
            {"text": "Только регистрация бизнеса", "correct": False},
        ],
    },
    {
        "id": "scenario_start_no_status",
        "difficulty": 3,
        "prompt": "У человека уже есть продажи, но юридического статуса ещё нет. Какой маршрут логичнее всего показать?",
        "options": [
            {"text": "Сразу обещать гарантию и запускать на заявку", "correct": False},
            {"text": "Регистрация бизнеса, затем РКО как следующий рабочий контур", "correct": True},
            {"text": "Только геопоиск отделений", "correct": False},
            {"text": "Только банковскую гарантию", "correct": False},
        ],
    },
    {
        "id": "scenario_existing_business",
        "difficulty": 3,
        "prompt": "У клиента уже есть ИП или ООО и нужны расчёты с контрагентами. Какой базовый продукт должен быть в приоритете?",
        "options": [
            {"text": "РКО", "correct": True},
            {"text": "Регистрация бизнеса", "correct": False},
            {"text": "Банковская гарантия в любом случае", "correct": False},
            {"text": "Отказ от банковского контура", "correct": False},
        ],
    },
    {
        "id": "scenario_wrong_cta",
        "difficulty": 3,
        "prompt": "Какой CTA нарушает продуктовую логику и правила?",
        "options": [
            {"text": "Узнать больше", "correct": False},
            {"text": "Перейти к оформлению", "correct": False},
            {"text": "Гарантированно получите продукт сегодня", "correct": True},
            {"text": "Открыть официальный маршрут", "correct": False},
        ],
    },
    {
        "id": "scenario_brand_page",
        "difficulty": 3,
        "prompt": "Агент хочет создать публичный Telegram-канал с названием, визуалом и подачей как у официального сервиса банка. Что верно?",
        "options": [
            {"text": "Это допустимо, если внизу мелко добавить слово «партнёр»", "correct": False},
            {"text": "Это рискованная мимикрия под бренд и так делать нельзя", "correct": True},
            {"text": "Так можно только для рекламы гарантий", "correct": False},
            {"text": "Это допустимо после 10 подтверждённых лидов", "correct": False},
        ],
    },
    {
        "id": "scenario_external_form",
        "difficulty": 3,
        "prompt": "Агент предлагает вести клиентов сначала на свою форму на стороннем домене, а потом вручную отправлять в банк. Как это оценивать?",
        "options": [
            {"text": "Нормально, если форма красивая", "correct": False},
            {"text": "Допустимо, если конверсия выше", "correct": False},
            {"text": "Это ломает контролируемый маршрут и повышает риск по согласию и качеству", "correct": True},
            {"text": "Это обязательно для всех агентов", "correct": False},
        ],
    },
    {
        "id": "scenario_guessing",
        "difficulty": 3,
        "prompt": "Почему экзамен построен из 20 вопросов, случайной выборки, перемешанных вариантов и высокого проходного балла?",
        "options": [
            {"text": "Чтобы тест можно было пройти наугад за пару минут", "correct": False},
            {"text": "Чтобы снизить шанс угадывания и повторного brute-force", "correct": True},
            {"text": "Чтобы админу было сложнее проверять анкеты", "correct": False},
            {"text": "Чтобы скрыть каталог продуктов", "correct": False},
        ],
    },
    {
        "id": "scenario_best_flow",
        "difficulty": 3,
        "prompt": "Какой поток для агента корректный?",
        "options": [
            {"text": "Агентский deeplink -> бот -> подбор/маршрут -> официальный переход по партнёрской ссылке", "correct": True},
            {"text": "Агентский deeplink -> личка агента -> сбор телефона -> ручная форма", "correct": False},
            {"text": "Публичный фейковый канал банка -> сторонний лендинг -> заявка", "correct": False},
            {"text": "Любой поток допустим, если высокий CR", "correct": False},
        ],
    },
    {
        "id": "scenario_manual_disclaimer",
        "difficulty": 3,
        "prompt": "Какой комплект раскрытия корректен для такого сервиса?",
        "options": [
            {"text": "Ничего раскрывать не нужно", "correct": False},
            {"text": "Партнёрский статус, справочный характер и ссылка на официальные условия", "correct": True},
            {"text": "Только логотип банка без текста", "correct": False},
            {"text": "Только устное пояснение агента", "correct": False},
        ],
    },
    {
        "id": "scenario_no_admin_submission",
        "difficulty": 3,
        "prompt": "Пользователь не добрал проходной балл по экзамену. Что должно произойти?",
        "options": [
            {"text": "Анкета всё равно уходит админу, чтобы он сам решил", "correct": False},
            {"text": "Заявка блокируется до следующей попытки после cooldown", "correct": True},
            {"text": "Бот автоматически одобряет агента", "correct": False},
            {"text": "Агент получает рабочую ссылку без модерации", "correct": False},
        ],
    },
]


def build_exam(seed: str) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    plan = [(1, 6), (2, 7), (3, 7)]
    for difficulty, count in plan:
        bucket = [item for item in QUESTION_POOL if int(item["difficulty"]) == difficulty]
        chosen = rng.sample(bucket, count)
        for question in chosen:
            prepared_options = list(question["options"])
            rng.shuffle(prepared_options)
            options: list[dict[str, str]] = []
            correct_option = ""
            for index, option in enumerate(prepared_options):
                option_id = chr(ord("a") + index)
                options.append({"id": option_id, "text": str(option["text"])})
                if option.get("correct"):
                    correct_option = option_id
            selected.append(
                {
                    "id": question["id"],
                    "difficulty": question["difficulty"],
                    "prompt": question["prompt"],
                    "options": options,
                    "correct_option": correct_option,
                }
            )
    return selected


def score_exam(questions: list[dict[str, Any]], answers: list[str]) -> int:
    score = 0
    for index, question in enumerate(questions):
        if index >= len(answers):
            break
        if answers[index] == question.get("correct_option"):
            score += 1
    return score


def progress_bar(current_index: int, total_questions: int) -> str:
    total_cells = 10
    ratio = 0 if total_questions <= 0 else current_index / float(total_questions)
    filled = max(0, min(total_cells, round(ratio * total_cells)))
    empty = total_cells - filled
    return f"{'■' * filled}{'□' * empty}"
