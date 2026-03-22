from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import escape_html


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class ContentCatalog:
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
        import json

        self._data = json.loads(self.path.read_text(encoding="utf-8"))
        self._mtime = current_mtime

    def get(self, key: str, default: Any = None) -> Any:
        self._load_if_needed()
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def text(self, key: str, default: str = "", **kwargs: Any) -> str:
        value = self.get(key, default)
        if not isinstance(value, str):
            return default
        safe_kwargs = {name: escape_html(item) for name, item in kwargs.items()}
        return value.format_map(_SafeDict(safe_kwargs))

    def list(self, key: str) -> list[Any]:
        value = self.get(key, [])
        return value if isinstance(value, list) else []

