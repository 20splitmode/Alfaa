from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .utils import turnover_band_label


SCENARIO_LABELS = {
    "daily_control": "Сейчас полезнее выстроить ежедневный контроль денег",
    "ip_rko": "Пора оформить статус и расчётный счёт",
    "rko_only": "Нужен расчётный счёт и рабочая операционка",
}

STATUS_LABELS = {
    "none": "без статуса",
    "self_employed": "самозанятый",
    "ip": "ИП",
    "ooo": "ООО",
}

SEGMENT_LABELS = {
    "starter": "старт и тест спроса",
    "growing": "рост и первые регулярные платежи",
    "registered": "уже оформленная деятельность",
}

PRIORITY_LABELS = {
    "money": "контроль денег и обязательств",
    "status": "понять, какой статус нужен",
    "account": "открыть счёт и отделить рабочие деньги",
    "application": "перейти к заявке без лишней теории",
}

PAIN_LABELS = {
    "messy_money": "личные и рабочие деньги смешаны",
    "unclear_status": "непонятно, какой статус нужен",
    "need_account": "нужен счёт для клиентов и порядка",
}


@dataclass(slots=True)
class DiagnosticResult:
    scenario: str
    scenario_label: str
    segment: str
    segment_label: str
    primary_pain: str
    pain_label: str
    current_state: str
    recommendation: str
    why_this: str
    next_step: str
    need_registration: bool


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status or "не указан")


def priority_label(priority: str) -> str:
    return PRIORITY_LABELS.get(priority, priority or "не указан")


def diagnose(profile: dict[str, Any]) -> DiagnosticResult:
    status = profile.get("status") or "none"
    turnover_band = profile.get("turnover_band") or "up_to_100"
    priority = profile.get("priority_focus") or "money"

    if status in {"ip", "ooo"}:
        segment = "registered"
    elif turnover_band in {"100_500", "500_1000", "1000_plus"}:
        segment = "growing"
    else:
        segment = "starter"

    if priority == "account" or (status in {"ip", "ooo"} and turnover_band in {"100_500", "500_1000", "1000_plus"}):
        scenario = "rko_only" if status in {"ip", "ooo"} else "ip_rko"
    elif priority in {"status", "application"}:
        scenario = "ip_rko" if status in {"none", "self_employed"} else "rko_only"
    else:
        scenario = "daily_control"

    primary_pain = {
        "money": "messy_money",
        "status": "unclear_status",
        "account": "need_account",
        "application": "need_account" if status in {"ip", "ooo"} else "unclear_status",
    }.get(priority, "messy_money")

    current_state = (
        f"Сейчас у вас статус {status_label(status)}, оборот {turnover_band_label(turnover_band)} "
        f"и фокус на задаче «{priority_label(priority)}»."
    )

    recommendation = {
        "daily_control": "Оптимальный следующий шаг: закрепить ежедневный контроль денег и обязательств, а уже потом переходить к оформлению.",
        "ip_rko": "Оптимальный следующий шаг: короткая заявка на регистрацию и расчётный счёт по вашему сценарию.",
        "rko_only": "Оптимальный следующий шаг: подобрать расчётный счёт и рабочую схему ежедневных операций.",
    }[scenario]

    why_this = {
        "daily_control": "Когда деньги ещё не ведутся регулярно, важнее вернуть управляемость и увидеть картину дня, чем торопиться с лишними действиями.",
        "ip_rko": "По вашему профилю видно, что вопрос уже не в интересе, а в переходе к рабочему формату без хаоса и лишней беготни.",
        "rko_only": "Юридическая база уже есть или почти готова, поэтому главное сейчас: счёт, дисциплина по деньгам и следующий шаг без лишнего трения.",
    }[scenario]

    next_step = {
        "daily_control": "Начните с ежедневного экрана, занесите доходы и расходы за сегодня, затем вернитесь к разделу «Моя ситуация».",
        "ip_rko": "Откройте раздел «Моя ситуация» или оставьте короткую заявку, если готовы двигаться без паузы.",
        "rko_only": "Проверьте раздел «Сегодня» и «Моя ситуация», затем переходите к заявке, если задача уже созрела.",
    }[scenario]

    return DiagnosticResult(
        scenario=scenario,
        scenario_label=SCENARIO_LABELS[scenario],
        segment=segment,
        segment_label=SEGMENT_LABELS[segment],
        primary_pain=primary_pain,
        pain_label=PAIN_LABELS[primary_pain],
        current_state=current_state,
        recommendation=recommendation,
        why_this=why_this,
        next_step=next_step,
        need_registration=status in {"none", "self_employed"} and scenario == "ip_rko",
    )
