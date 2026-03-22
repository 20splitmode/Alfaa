from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_bool(name: str, default: bool = False) -> bool:
    value = _get(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = _get(name)
    if not value:
        return default
    return int(value)


def _get_webhook_port(default: int = 8080) -> int:
    explicit = _get("WEBHOOK_PORT")
    if explicit:
        return int(explicit)
    render_port = _get("PORT")
    if render_port:
        return int(render_port)
    return default


def _get_admin_ids() -> tuple[int, ...]:
    raw = ",".join(filter(None, [_get("ADMIN_IDS"), _get("ADMIN_ID")]))
    if not raw:
        return ()
    return tuple(int(item.strip()) for item in raw.split(",") if item.strip())


def _get_admin_usernames() -> tuple[str, ...]:
    raw = _get("ADMIN_USERNAMES")
    if not raw:
        return ()
    return tuple(item.strip().lstrip("@").lower() for item in raw.split(",") if item.strip())


@dataclass(slots=True)
class Settings:
    telegram_token: str
    bot_name: str
    bot_username: str
    admin_ids: tuple[int, ...]
    admin_usernames: tuple[str, ...]
    timezone: str
    use_webhook: bool
    webhook_base_url: str
    webhook_path: str
    webhook_host: str
    webhook_port: int
    offer_url: str
    agent_offer_path: Path
    lead_webhook_url: str
    postback_url: str
    google_sheets_webhook_url: str
    yandex_maps_api_key: str
    yandex_maps_lang: str
    root_dir: Path
    data_dir: Path
    export_dir: Path
    db_path: Path
    content_path: Path
    product_catalog_path: Path

    @property
    def webhook_url(self) -> str:
        base = self.webhook_base_url.rstrip("/")
        path = self.webhook_path if self.webhook_path.startswith("/") else f"/{self.webhook_path}"
        return f"{base}{path}" if base else ""

    @property
    def reminder_plan(self) -> dict[str, int]:
        return {
            "followup_10m": 10,
            "followup_1d": 24 * 60,
            "followup_3d": 3 * 24 * 60,
            "followup_7d": 7 * 24 * 60,
        }

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.content_path.parent.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN is required")
        if self.use_webhook and not self.webhook_base_url:
            raise ValueError("WEBHOOK_BASE_URL is required when USE_WEBHOOK=1")

    def is_admin(self, telegram_id: int | None, username: str | None = None) -> bool:
        if telegram_id and telegram_id in self.admin_ids:
            return True
        normalized = (username or "").strip().lstrip("@").lower()
        return bool(normalized and normalized in self.admin_usernames)


def load_settings(env_path: str | Path | None = None) -> Settings:
    env_file = Path(env_path) if env_path else ROOT_DIR / ".env"
    _load_env_file(env_file)
    load_dotenv(env_file, override=False)
    settings = Settings(
        telegram_token=_get("TELEGRAM_TOKEN"),
        bot_name=_get("BOT_NAME", "Бизнес-Старт"),
        bot_username=_get("BOT_USERNAME"),
        admin_ids=_get_admin_ids(),
        admin_usernames=_get_admin_usernames(),
        timezone=_get("TIMEZONE", "Europe/Moscow"),
        use_webhook=_get_bool("USE_WEBHOOK", False),
        webhook_base_url=_get("WEBHOOK_BASE_URL") or _get("RENDER_EXTERNAL_URL"),
        webhook_path=_get("WEBHOOK_PATH", "/telegram/webhook"),
        webhook_host=_get("WEBHOOK_HOST", "0.0.0.0"),
        webhook_port=_get_webhook_port(8080),
        offer_url=_get("OFFER_URL"),
        agent_offer_path=Path(_get("AGENT_OFFER_PATH", str(ROOT_DIR / "data" / "assets" / "agent-referral-guide.pdf"))),
        lead_webhook_url=_get("LEAD_WEBHOOK_URL"),
        postback_url=_get("POSTBACK_URL"),
        google_sheets_webhook_url=_get("GOOGLE_SHEETS_WEBHOOK_URL"),
        yandex_maps_api_key=_get("YANDEX_MAPS_API_KEY"),
        yandex_maps_lang=_get("YANDEX_MAPS_LANG", "ru_RU"),
        root_dir=ROOT_DIR,
        data_dir=ROOT_DIR / "data",
        export_dir=ROOT_DIR / "exports",
        db_path=ROOT_DIR / "data" / "business_start.db",
        content_path=ROOT_DIR / "data" / "content" / "messages.json",
        product_catalog_path=ROOT_DIR / "data" / "content" / "product_catalog.json",
    )
    settings.ensure_directories()
    settings.validate()
    return settings
