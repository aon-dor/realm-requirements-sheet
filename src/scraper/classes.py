from __future__ import annotations

from html.parser import HTMLParser

from src.models.schema import ClassRecord, slugify

CLASSES_PATH = "/wiki/classes"


class _ClassesHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self.records: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        if tag == "a":
            href = attr_map.get("href", "")
            self._current_href = href if href.startswith("/wiki/") else None
            return

        if tag == "img" and self._current_href:
            src = attr_map.get("src") or attr_map.get("data-src") or ""
            alt = (attr_map.get("alt") or "").strip()
            if src and alt:
                self.records.append((alt, src, self._current_href))

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._current_href = None


def parse_classes_html(html: str, base_url: str = "https://www.realmeye.com") -> list[ClassRecord]:
    parser = _ClassesHTMLParser()
    parser.feed(html)

    seen_ids: set[str] = set()
    records: list[ClassRecord] = []

    for name, icon_src, href in parser.records:
        record_id = f"class-{slugify(name)}"
        if record_id in seen_ids:
            continue
        seen_ids.add(record_id)
        records.append(
            ClassRecord(
                id=record_id,
                name=name,
                icon_url=_make_absolute(base_url, icon_src),
                page_url=_make_absolute(base_url, href),
            )
        )

    return sorted(records, key=lambda row: row.name.lower())


def _make_absolute(base_url: str, path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        return path_or_url
    if path_or_url.startswith("//"):
        return f"https:{path_or_url}"
    return f"{base_url}{path_or_url}" if path_or_url.startswith("/") else f"{base_url}/{path_or_url}"
