from __future__ import annotations

import hashlib
from dataclasses import dataclass


FRAUD_STATUS_LABELS = {
    "good": "GOOD",
    "hold": "HOLD",
    "reject": "REJECT",
}

AGENT_STATUS_LABELS = {
    "draft": "черновик",
    "pending": "на проверке",
    "approved": "одобрен",
    "rejected": "отклонён",
    "banned": "заблокирован",
}

AGENT_LEVEL_LABELS = {
    "junior": "junior",
    "pro": "pro",
    "elite": "elite",
}

DEFAULT_AGENT_SHARE = {
    "junior": 30.0,
    "pro": 40.0,
    "elite": 50.0,
}

FRAUD_REASON_LABELS = {
    "fields_complete": "все поля заполнены",
    "old_enough_profile": "профиль не выглядит одноразовым",
    "fast_form": "слишком быстрое заполнение",
    "duplicate_phone_recent": "повтор телефона за последние 30 дней",
    "user_repeat_24h": "повторные заявки с одного Telegram-аккаунта за 24 часа",
    "agent_spike": "рост потока от агента за короткий интервал",
    "agent_burst": "аномальный всплеск трафика от агента",
    "agent_high_reject_ratio": "высокая доля отклонений у агента",
}


@dataclass(slots=True)
class LeadFraudResult:
    score: int
    status: str
    reasons: list[str]
    auto_block_agent: bool


def generate_referral_code(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest().upper()
    return f"AG{digest[:10]}"


def default_agent_share(level: str) -> float:
    return float(DEFAULT_AGENT_SHARE.get(level, DEFAULT_AGENT_SHARE["junior"]))


def lead_fraud_status_label(status: str) -> str:
    return FRAUD_STATUS_LABELS.get(status, status.upper())


def agent_status_label(status: str) -> str:
    return AGENT_STATUS_LABELS.get(status, status)


def agent_level_label(level: str) -> str:
    return AGENT_LEVEL_LABELS.get(level, level)


def fraud_reason_label(code: str) -> str:
    return FRAUD_REASON_LABELS.get(code, code)


def score_lead(
    *,
    form_duration_sec: int | None,
    duplicate_recent: bool,
    recent_user_leads: int,
    fields_complete: bool,
    user_age_sec: int | None,
    agent_recent_leads: int = 0,
    agent_total_leads: int = 0,
    agent_rejected_leads: int = 0,
) -> LeadFraudResult:
    score = 35
    reasons: list[str] = []

    if fields_complete:
        score += 15
        reasons.append("fields_complete")

    if user_age_sec is not None and user_age_sec >= 60:
        score += 10
        reasons.append("old_enough_profile")

    if form_duration_sec is None:
        pass
    elif form_duration_sec >= 20:
        score += 20
    elif form_duration_sec >= 10:
        score += 10
    else:
        score -= 40
        reasons.append("fast_form")

    if duplicate_recent:
        score -= 50
        reasons.append("duplicate_phone_recent")

    if recent_user_leads <= 0:
        score += 10
    else:
        score -= min(20, 5 * recent_user_leads)
        reasons.append("user_repeat_24h")

    if agent_recent_leads >= 8:
        score -= 35
        reasons.append("agent_burst")
    elif agent_recent_leads >= 4:
        score -= 15
        reasons.append("agent_spike")

    reject_ratio = 0.0
    if agent_total_leads > 0:
        reject_ratio = agent_rejected_leads / float(agent_total_leads)
    if agent_total_leads >= 10 and reject_ratio > 0.30:
        score -= 20
        reasons.append("agent_high_reject_ratio")

    score = max(0, min(100, score))
    if score >= 70:
        status = "good"
    elif score >= 40:
        status = "hold"
    else:
        status = "reject"

    auto_block_agent = bool(
        agent_total_leads >= 10
        and (
            reject_ratio > 0.35
            or agent_recent_leads >= 10
        )
    )
    return LeadFraudResult(score=score, status=status, reasons=reasons, auto_block_agent=auto_block_agent)
