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
SPECIAL_TIER_ANCHOR_PATTERN = re.compile(r"^(?:tier-)?(st|ut)$", re.IGNORECASE)
UNTIERED_ANCHOR_PATTERN = re.compile(r"^untiered(?:-[a-z0-9-]+)?$", re.IGNORECASE)
SET_ANCHOR_PATTERN = re.compile(r"^set(?:-[a-z0-9-]+)?$", re.IGNORECASE)
SPECIAL_TIER_PATTERN = re.compile(r"\b(ST|UT)\b", re.IGNORECASE)
CLASS_NAMES = {
    "archer",
    "assassin",
    "bard",
    "huntress",
    "knight",
    "kensei",
    "mystic",
    "necromancer",
    "ninja",
    "paladin",
    "priest",
    "rogue",
    "samurai",
    "sorcerer",
    "summoner",
    "trickster",
    "warrior",
    "wizard",
}


class _ItemsTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_tier: str | None = None
        self._in_tr = False
        self._in_cell = False
        self._row: dict[str, object] | None = None
        self._cell_text: list[str] = []
        self._current_link: dict[str, object] | None = None
        self.rows: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}

        if tag == "a":
            tier_anchor = (attr_map.get("name") or "").strip().lower()
            tier_match = TIER_ANCHOR_PATTERN.match(tier_anchor)
            if tier_match:
                self._current_tier = f"T{tier_match.group(1)}"
            else:
                special_tier_match = SPECIAL_TIER_ANCHOR_PATTERN.match(tier_anchor)
                if special_tier_match:
                    self._current_tier = special_tier_match.group(1).upper()
                elif UNTIERED_ANCHOR_PATTERN.match(tier_anchor):
                    self._current_tier = "UT"
                elif SET_ANCHOR_PATTERN.match(tier_anchor):
                    self._current_tier = "ST"

            if self._in_tr and self._in_cell:
                self._current_link = {
                    "href": attr_map.get("href", ""),
                    "text": "",
                    "has_img": False,
                    "img_src": "",
                    "img_alt": "",
                }
            return

        if tag == "tr":
            self._in_tr = True
            self._row = {"tier": self._current_tier, "cells": [], "links": [], "images": []}
            return

        if tag in {"td", "th"} and self._in_tr:
            self._in_cell = True
            self._cell_text = []
            return

        if tag == "img" and self._in_tr and self._row is not None:
            src = attr_map.get("src") or attr_map.get("data-src") or ""
            alt = (attr_map.get("alt") or "").strip()
            image = {"src": src, "alt": alt}
            cast_images = self._row["images"]
            assert isinstance(cast_images, list)
            cast_images.append(image)
            if self._current_link is not None:
                self._current_link["has_img"] = True
                self._current_link["img_src"] = src
                self._current_link["img_alt"] = alt

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return

        if self._in_cell:
            self._cell_text.append(text)

        if self._current_link is not None:
            link_text = str(self._current_link.get("text", "")).strip()
            self._current_link["text"] = f"{link_text} {text}".strip() if link_text else text

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_link is not None and self._row is not None:
            cast_links = self._row["links"]
            assert isinstance(cast_links, list)
            cast_links.append(self._current_link)
            self._current_link = None
            return

        if tag in {"td", "th"} and self._in_tr and self._row is not None:
            cell_value = " ".join(self._cell_text).strip()
            cast_cells = self._row["cells"]
            assert isinstance(cast_cells, list)
            cast_cells.append(cell_value)
            self._cell_text = []
            self._in_cell = False
            return

        if tag == "tr" and self._in_tr and self._row is not None:
            self.rows.append(self._row)
            self._row = None
            self._in_tr = False


def parse_items_html(html: str, base_url: str = "https://www.realmeye.com", default_item_type: str | None = None) -> list[ItemRecord]:
    parser = _ItemsTableParser()
    parser.feed(html)

    records: list[ItemRecord] = []
    seen_ids: set[str] = set()

    for row in parser.rows:
        links = [link for link in _as_list(row.get("links")) if str(link.get("href", "")).startswith("/wiki/")]
        images = _as_list(row.get("images"))
        cells = [str(cell) for cell in _as_list(row.get("cells")) if str(cell).strip()]
        row_tier = str(row.get("tier") or "").strip() or None

        link = _choose_item_link(links, bool(images))
        if link is None:
            continue

        href = str(link.get("href", ""))
        icon_src = str(link.get("img_src", "")).strip() or _first_image_src(images)
        name = str(link.get("text", "")).strip() or str(link.get("img_alt", "")).strip() or _first_image_alt(images)
        if not href or not icon_src or not name:
            continue

        if name.lower() in CLASS_NAMES:
            continue

        row_text = " ".join([name, *cells])
        special_tier_match = SPECIAL_TIER_PATTERN.search(row_text)
        if special_tier_match:
            tier = special_tier_match.group(1).upper()
        else:
            tier_match = TIER_PATTERN.search(row_text)
            tier = row_tier or (f"T{tier_match.group(1)}" if tier_match else None)

        item_type = default_item_type or (cells[2] if len(cells) > 2 and cells[2] else None)

        base_record = ItemRecord(
            id=f"item-{slugify(name)}",
            name=name,
            icon_url=_make_absolute(base_url, icon_src),
            page_url=_make_absolute(base_url, href),
            item_type=item_type,
            tier=tier,
        )

        for record in _expand_tiered_ring_bundle(base_record):
            if record.id in seen_ids:
                continue
            seen_ids.add(record.id)
            records.append(record)

    return sorted(records, key=lambda row: row.name.lower())


def _as_list(value: object) -> list[dict[str, object]]:
    return value if isinstance(value, list) else []


def _choose_item_link(links: list[dict[str, object]], has_row_images: bool) -> dict[str, object] | None:
    if not links:
        return None

    icon_links = [link for link in links if link.get("has_img")]
    if icon_links:
        return icon_links[0]

    if len(links) == 1 and has_row_images:
        return links[0]

    if len(links) == 1 and str(links[0].get("text", "")).strip():
        return links[0]

    return None


def _first_image_src(images: list[dict[str, object]]) -> str:
    for image in images:
        src = str(image.get("src", "")).strip()
        if src:
            return src
    return ""


def _first_image_alt(images: list[dict[str, object]]) -> str:
    for image in images:
        alt = str(image.get("alt", "")).strip()
        if alt:
            return alt
    return ""


def _expand_tiered_ring_bundle(record: ItemRecord) -> list[ItemRecord]:
    if record.item_type != "Ring" or record.tier is not None:
        return [record]

    if not record.name.endswith(" Rings"):
        return [record]

    expanded: list[ItemRecord] = []
    for tier_number in range(1, 8):
        tier = f"T{tier_number}"
        name = f"{record.name} ({tier})"
        expanded.append(
            ItemRecord(
                id=f"item-{slugify(name)}",
                name=name,
                icon_url=record.icon_url,
                page_url=record.page_url,
                item_type=record.item_type,
                tier=tier,
            )
        )

    return expanded


def _make_absolute(base_url: str, path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        return path_or_url
    if path_or_url.startswith("//"):
        return f"https:{path_or_url}"
    return f"{base_url}{path_or_url}" if path_or_url.startswith("/") else f"{base_url}/{path_or_url}"
