from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from .config import Settings


class IntegrationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=15)

    async def close(self) -> None:
        await self.client.aclose()

    async def send_lead(self, user: dict[str, Any], lead: dict[str, Any]) -> list[dict[str, Any]]:
        payload = self._build_payload(user, lead, event="lead_created")
        return await self._fan_out(payload)

    async def send_status_update(self, user: dict[str, Any], lead: dict[str, Any]) -> list[dict[str, Any]]:
        payload = self._build_payload(user, lead, event="lead_status_changed")
        return await self._fan_out(payload)

    async def get_currency_rates(self, codes: tuple[str, ...] = ("USD", "EUR", "CNY")) -> dict[str, Any]:
        url = "https://www.cbr.ru/scripts/XML_daily.asp"
        response = await self.client.get(url)
        response.raise_for_status()
        try:
            xml_text = response.content.decode("windows-1251")
        except UnicodeDecodeError:
            xml_text = response.text
        root = ElementTree.fromstring(xml_text)
        result: dict[str, Any] = {"date": root.attrib.get("Date", ""), "rates": {}}
        wanted = set(codes)
        for node in root.findall("Valute"):
            code = (node.findtext("CharCode") or "").strip().upper()
            if code not in wanted:
                continue
            nominal = int((node.findtext("Nominal") or "1").strip())
            value = (node.findtext("Value") or "").strip().replace(",", ".")
            name = (node.findtext("Name") or "").strip()
            try:
                numeric_value = float(value)
            except ValueError:
                continue
            result["rates"][code] = {
                "name": name,
                "nominal": nominal,
                "value": numeric_value,
            }
        return result

    async def geocode(self, query: str) -> dict[str, Any]:
        if not self.settings.yandex_maps_api_key:
            raise ValueError("YANDEX_MAPS_API_KEY is not configured")
        response = await self.client.get(
            "https://geocode-maps.yandex.ru/1.x/",
            params={
                "apikey": self.settings.yandex_maps_api_key,
                "geocode": query,
                "format": "json",
                "lang": self.settings.yandex_maps_lang,
                "results": 1,
            },
        )
        response.raise_for_status()
        payload = response.json()
        members = (
            payload.get("response", {})
            .get("GeoObjectCollection", {})
            .get("featureMember", [])
        )
        if not members:
            return {}
        geo_object = members[0].get("GeoObject", {})
        pos = (
            geo_object.get("Point", {})
            .get("pos", "")
            .split()
        )
        lon = float(pos[0]) if len(pos) == 2 else None
        lat = float(pos[1]) if len(pos) == 2 else None
        return {
            "address": geo_object.get("metaDataProperty", {})
            .get("GeocoderMetaData", {})
            .get("text", query),
            "lat": lat,
            "lon": lon,
            "raw": geo_object,
        }

    async def search_nearby_points(self, lat: float, lon: float, *, kind: str, limit: int = 3) -> list[dict[str, Any]]:
        amenity = "atm" if kind == "atm" else "bank"
        query = f"""
[out:json][timeout:20];
(
  node["amenity"="{amenity}"](around:5000,{lat},{lon});
  way["amenity"="{amenity}"](around:5000,{lat},{lon});
  relation["amenity"="{amenity}"](around:5000,{lat},{lon});
);
out center tags;
"""
        response = await self.client.post(
            "https://overpass-api.de/api/interpreter",
            content=query.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        response.raise_for_status()
        payload = response.json()
        items = self._normalize_points(payload.get("elements") or [], lat, lon)
        if not items:
            return []
        branded = [item for item in items if item["is_alfa"]]
        source = branded or items
        return source[:limit]

    def maps_search_url(self, query: str) -> str:
        return f"https://yandex.ru/maps/?text={quote_plus(query)}"

    def maps_route_url(self, lat: float | None, lon: float | None, *, query: str = "") -> str:
        if lat is not None and lon is not None:
            return f"https://yandex.ru/maps/?ll={lon},{lat}&z=16"
        return self.maps_search_url(query)

    def maps_nearby_url(self, lat: float, lon: float, *, query: str = "") -> str:
        if query:
            return f"https://yandex.ru/maps/?ll={lon},{lat}&z=15&text={quote_plus(query)}"
        return f"https://yandex.ru/maps/?ll={lon},{lat}&z=15"

    def alfa_points_search_url(self, city_or_query: str) -> str:
        return self.maps_search_url(f"Альфа-Банк {city_or_query}")

    def _build_payload(self, user: dict[str, Any], lead: dict[str, Any], *, event: str) -> dict[str, Any]:
        return {
            "event": event,
            "telegram_user_id": user.get("telegram_id"),
            "lead_id": lead.get("id"),
            "name": lead.get("name"),
            "phone": lead.get("phone"),
            "city": lead.get("city"),
            "contact_time": lead.get("contact_time"),
            "legal_status": lead.get("current_status") or user.get("status"),
            "lead_status": lead.get("lead_status"),
            "temperature": lead.get("temperature"),
            "agent_id": lead.get("agent_id"),
            "agent_referral_code": lead.get("referral_code"),
            "fraud_score": lead.get("fraud_score"),
            "fraud_status": lead.get("fraud_status"),
            "segment": lead.get("segment") or user.get("segment"),
            "scenario": lead.get("scenario") or user.get("scenario"),
            "source": lead.get("source") or user.get("source"),
            "campaign": lead.get("campaign") or user.get("campaign"),
            "creative": lead.get("creative") or user.get("creative"),
            "utm_source": user.get("utm_source"),
            "utm_medium": user.get("utm_medium"),
            "utm_campaign": user.get("utm_campaign"),
            "utm_content": user.get("utm_content"),
            "utm_term": user.get("utm_term"),
        }

    async def _fan_out(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for url in (
            self.settings.lead_webhook_url,
            self.settings.postback_url,
            self.settings.google_sheets_webhook_url,
        ):
            if not url:
                continue
            results.append(await self._post(url, payload))
        return results

    async def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            body: dict[str, Any] | str
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                body = response.json()
            else:
                body = response.text[:500]
            return {"url": url, "ok": True, "status_code": response.status_code, "body": body}
        except Exception as exc:
            return {"url": url, "ok": False, "error": str(exc)}

    def _normalize_points(self, elements: list[dict[str, Any]], base_lat: float, base_lon: float) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for element in elements:
            lat = element.get("lat")
            lon = element.get("lon")
            if lat is None or lon is None:
                center = element.get("center") or {}
                lat = center.get("lat")
                lon = center.get("lon")
            if lat is None or lon is None:
                continue
            tags = element.get("tags") or {}
            title = (
                tags.get("name")
                or tags.get("brand")
                or tags.get("operator")
                or ("Банкомат" if tags.get("amenity") == "atm" else "Отделение")
            )
            address = self._format_address(tags)
            distance_m = round(self._haversine(base_lat, base_lon, float(lat), float(lon)))
            tag_blob = " ".join(str(value) for value in tags.values()).lower()
            items.append(
                {
                    "title": title,
                    "address": address,
                    "lat": float(lat),
                    "lon": float(lon),
                    "distance_m": distance_m,
                    "is_alfa": any(marker in tag_blob for marker in ("альфа", "alfa", "alpha")),
                }
            )
        items.sort(key=lambda item: item["distance_m"])
        return items

    def _format_address(self, tags: dict[str, Any]) -> str:
        full = str(tags.get("addr:full") or "").strip()
        if full:
            return full
        parts = [
            str(tags.get("addr:city") or "").strip(),
            str(tags.get("addr:street") or "").strip(),
            str(tags.get("addr:housenumber") or "").strip(),
        ]
        cleaned = [part for part in parts if part]
        return ", ".join(cleaned) or "Адрес не указан"

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371000
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)
        base = (
            sin(delta_lat / 2) ** 2
            + cos(radians(lat1)) * cos(radians(lat2)) * sin(delta_lon / 2) ** 2
        )
        return 2 * radius * asin(sqrt(base))
