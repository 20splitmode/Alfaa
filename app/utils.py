from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl


UTC = timezone.utc
PHONE_DIGITS_RE = re.compile(r"\D+")
NUMBER_RE = re.compile(r"\d+")


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return now_utc().isoformat()


def future_iso(*, minutes: int = 0, hours: int = 0, days: int = 0) -> str:
    return (now_utc() + timedelta(minutes=minutes, hours=hours, days=days)).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def escape_html(value: Any) -> str:
    return html.escape(str(value or ""))


def extract_start_argument(text: str | None) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def normalize_phone(raw: str | None) -> str:
    digits = PHONE_DIGITS_RE.sub("", raw or "")
    if len(digits) == 10:
        digits = f"7{digits}"
    elif len(digits) == 11 and digits.startswith("8"):
        digits = f"7{digits[1:]}"
    if len(digits) < 11:
        return ""
    return f"+{digits}"


def phone_is_valid(raw: str | None) -> bool:
    return bool(normalize_phone(raw))


def parse_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    match = NUMBER_RE.search(raw.replace(" ", ""))
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def turnover_band_from_value(value: int | None) -> str:
    if value is None or value <= 0:
        return "unknown"
    if value < 100_000:
        return "up_to_100"
    if value < 500_000:
        return "100_500"
    if value < 1_000_000:
        return "500_1000"
    return "1000_plus"


def turnover_band_label(band: str) -> str:
    mapping = {
        "up_to_100": "до 100 000 ₽",
        "100_500": "100 000–500 000 ₽",
        "500_1000": "500 000–1 000 000 ₽",
        "1000_plus": "более 1 000 000 ₽",
        "unknown": "не указан",
    }
    return mapping.get(band, band or "не указан")


def parse_tracking_payload(payload: str) -> dict[str, str]:
    data = {
        "source": "",
        "campaign": "",
        "creative": "",
        "utm_source": "",
        "utm_medium": "",
        "utm_campaign": "",
        "utm_content": "",
        "utm_term": "",
        "start_payload": payload.strip(),
    }
    raw = payload.strip()
    if not raw:
        return data
    if "=" not in raw:
        data["source"] = raw
        return data
    normalized = raw.replace("|", "&").replace(";", "&").replace("__", "&")
    for key, value in parse_qsl(normalized, keep_blank_values=True):
        key = key.strip().lower()
        clean = value.strip()
        if key in data:
            data[key] = clean
        elif key == "utm_source":
            data["utm_source"] = clean
        elif key == "utm_medium":
            data["utm_medium"] = clean
        elif key == "utm_campaign":
            data["utm_campaign"] = clean
        elif key == "utm_content":
            data["utm_content"] = clean
        elif key == "utm_term":
            data["utm_term"] = clean
        elif key in {"src", "source"}:
            data["source"] = clean
        elif key in {"cmp", "campaign"}:
            data["campaign"] = clean
        elif key in {"crt", "creative"}:
            data["creative"] = clean
    if not data["source"]:
        data["source"] = data["utm_source"]
    if not data["campaign"]:
        data["campaign"] = data["utm_campaign"]
    if not data["creative"]:
        data["creative"] = data["utm_content"]
    return data


def compact_name(full_name: str | None, fallback: str = "Коллега") -> str:
    value = (full_name or "").strip()
    if not value:
        return fallback
    return value.split()[0]
