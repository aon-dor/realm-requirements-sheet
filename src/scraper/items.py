from __future__ import annotations

import re
from html.parser import HTMLParser

from src.models.schema import ItemRecord, slugify

ITEMS_PATH = "/wiki/items"
TIER_PATTERN = re.compile(r"\bT(\d{1,2})\b", re.IGNORECASE)


class _ItemsTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_row = False
        self._in_cell = False
        self._current_href: str | None = None
        self._in_link = False
        self._current_link_text: list[str] = []
        self._current_row_cells: list[str] = []
        self._current_cell_text: list[str] = []
        self._current_icon_src: str | None = None
        self._current_icon_alt: str | None = None
        self.rows: list[dict[str, str | list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}

        if tag == "tr":
            self._in_row = True
            self._current_row_cells = []
            self._current_icon_src = None
            self._current_icon_alt = None
            self._current_href = None
            self._current_link_text = []
            self._in_link = False
            return

        if not self._in_row:
            return

        if tag == "td":
            self._in_cell = True
            self._current_cell_text = []
            return

        if tag == "a":
            href = attr_map.get("href", "")
            if href.startswith("/wiki/"):
                self._current_href = href
                self._in_link = True
            return

        if tag == "img":
            src = attr_map.get("src") or attr_map.get("data-src") or ""
            alt = (attr_map.get("alt") or "").strip()
            if src:
                self._current_icon_src = src
            if alt:
                self._current_icon_alt = alt

    def handle_data(self, data: str) -> None:
        if not self._in_row:
            return

        text = data.strip()
        if not text:
            return

        if self._in_cell:
            self._current_cell_text.append(text)
        if self._in_link:
            self._current_link_text.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_row and self._in_cell:
            self._in_cell = False
            self._current_row_cells.append(" ".join(self._current_cell_text).strip())
            return

        if tag == "a":
            self._in_link = False
            return

        if tag == "tr" and self._in_row:
            self._in_row = False
            row = {
                "href": self._current_href or "",
                "name": " ".join(self._current_link_text).strip() or (self._current_icon_alt or ""),
                "icon_src": self._current_icon_src or "",
                "cells": self._current_row_cells,
            }
            self.rows.append(row)


def parse_items_html(html: str, base_url: str = "https://www.realmeye.com") -> list[ItemRecord]:
    parser = _ItemsTableParser()
    parser.feed(html)

    records: list[ItemRecord] = []
    seen_ids: set[str] = set()

    for row in parser.rows:
        href = str(row["href"])
        icon_src = str(row["icon_src"])
        name = str(row["name"]).strip()
        cells = [str(cell) for cell in row["cells"]]

        if not href.startswith("/wiki/") or not icon_src or not name:
            continue

        tier_match = TIER_PATTERN.search(" ".join(cells))
        tier = f"T{tier_match.group(1)}" if tier_match else None
        item_type = cells[2] if len(cells) > 2 and cells[2] else None

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
