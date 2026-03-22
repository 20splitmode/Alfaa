from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProductCatalog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._mtime: float | None = None
        self._data: dict[str, Any] = {}

    def _load_if_needed(self) -> None:
        if not self.path.exists():
            self._data = {}
            self._mtime = None
            return
        current_mtime = self.path.stat().st_mtime
        if self._mtime == current_mtime:
            return
        self._data = json.loads(self.path.read_text(encoding="utf-8"))
        self._mtime = current_mtime

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        self._load_if_needed()
        return (self._data.get("products") or {}).get(product_id)

    def get_situation(self, situation_id: str) -> dict[str, Any] | None:
        self._load_if_needed()
        return (self._data.get("situations") or {}).get(situation_id)

    def get_industry(self, industry_id: str) -> dict[str, Any] | None:
        self._load_if_needed()
        return (self._data.get("industries") or {}).get(industry_id)

    def catalog_page(self, page: int) -> list[str]:
        self._load_if_needed()
        pages = self._data.get("catalog_pages") or []
        if 0 <= page < len(pages):
            return list(pages[page])
        return []

    def situations_page(self, page: int) -> list[str]:
        self._load_if_needed()
        pages = self._data.get("situation_pages") or []
        if 0 <= page < len(pages):
            return list(pages[page])
        return []

    def industries_page(self) -> list[str]:
        self._load_if_needed()
        return list(self._data.get("industry_page") or [])

    def tariff_rule(self, rule_id: str) -> dict[str, Any] | None:
        self._load_if_needed()
        return (self._data.get("tariff_rules") or {}).get(rule_id)

    def tariff_rules(self) -> dict[str, Any]:
        self._load_if_needed()
        return dict(self._data.get("tariff_rules") or {})
