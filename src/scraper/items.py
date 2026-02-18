from __future__ import annotations

import re
from html.parser import HTMLParser

from src.models.schema import ItemRecord, slugify

ITEMS_PATH = "/wiki/equipment"
CATEGORY_PATHS: dict[str, str] = {
    "/wiki/weapons": "Weapon",
    "/wiki/ability-items": "Ability",
    "/wiki/armor": "Armor",
    "/wiki/rings": "Ring",
}
TIER_PATTERN = re.compile(r"\bT(\d{1,2})\b", re.IGNORECASE)
TIER_ANCHOR_PATTERN = re.compile(r"^tier-(\d{1,2})$", re.IGNORECASE)


class _ItemsTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_tier: str | None = None
        self._current_item: dict[str, str] | None = None
        self.rows: list[dict[str, str | list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}

        if tag == "a":
            tier_anchor = (attr_map.get("name") or "").strip().lower()
            tier_match = TIER_ANCHOR_PATTERN.match(tier_anchor)
            if tier_match:
                self._current_tier = f"T{tier_match.group(1)}"

            href = attr_map.get("href", "")
            if href.startswith("/wiki/"):
                self._current_item = {"href": href, "tier": self._current_tier or ""}
            return

        if tag == "img" and self._current_item is not None:
            src = attr_map.get("src") or attr_map.get("data-src") or ""
            alt = (attr_map.get("alt") or "").strip()
            if src:
                self._current_item["icon_src"] = src
            if alt:
                self._current_item["name"] = alt

    def handle_data(self, data: str) -> None:
        if self._current_item is None:
            return

        text = data.strip()
        if not text:
            return

        if "name" not in self._current_item:
            self._current_item["name"] = text

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_item is None:
            return

        row = {
            "href": self._current_item.get("href", ""),
            "name": self._current_item.get("name", ""),
            "icon_src": self._current_item.get("icon_src", ""),
            "tier": self._current_item.get("tier", ""),
            "cells": [],
        }
        self.rows.append(row)
        self._current_item = None


def parse_items_html(html: str, base_url: str = "https://www.realmeye.com", default_item_type: str | None = None) -> list[ItemRecord]:
    parser = _ItemsTableParser()
    parser.feed(html)

    records: list[ItemRecord] = []
    seen_ids: set[str] = set()

    for row in parser.rows:
        href = str(row["href"])
        icon_src = str(row["icon_src"])
        name = str(row["name"]).strip()
        cells = [str(cell) for cell in row["cells"]]
        row_tier = str(row.get("tier", "")).strip() or None

        if not href.startswith("/wiki/") or not icon_src or not name:
            continue

        tier_match = TIER_PATTERN.search(" ".join(cells))
        tier = row_tier or (f"T{tier_match.group(1)}" if tier_match else None)
        item_type = default_item_type or (cells[2] if len(cells) > 2 and cells[2] else None)

        record_id = f"item-{slugify(name)}"
        if record_id in seen_ids:
            continue
        seen_ids.add(record_id)

        records.append(
            ItemRecord(
                id=record_id,
                name=name,
                icon_url=_make_absolute(base_url, icon_src),
                page_url=_make_absolute(base_url, href),
                item_type=item_type,
                tier=tier,
            )
        )

    return sorted(records, key=lambda row: row.name.lower())


def _make_absolute(base_url: str, path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        return path_or_url
    if path_or_url.startswith("//"):
        return f"https:{path_or_url}"
    return f"{base_url}{path_or_url}" if path_or_url.startswith("/") else f"{base_url}/{path_or_url}"
