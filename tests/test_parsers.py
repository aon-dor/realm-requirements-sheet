from pathlib import Path

from src.scraper.classes import parse_classes_html
from src.scraper.items import parse_items_html


def test_parse_classes_html_extracts_records() -> None:
    html = Path("tests/fixtures/classes/sample_classes.html").read_text(encoding="utf-8")
    records = parse_classes_html(html)

    assert len(records) == 2
    assert records[0].id == "class-knight"
    assert records[0].icon_url == "https://www.realmeye.com/img/knight.png"


def test_parse_items_html_extracts_records() -> None:
    html = Path("tests/fixtures/items/sample_items.html").read_text(encoding="utf-8")
    records = parse_items_html(html)

    assert len(records) == 2
    assert records[0].id == "item-tiered-robe"
    assert records[1].tier == "T10"
