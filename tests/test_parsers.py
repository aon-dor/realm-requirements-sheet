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


def test_parse_items_html_prefers_ut_st_and_ignores_classes() -> None:
    html = """
    <html><body>
      <a name="tier-14"></a>
      <table>
        <tr>
          <td><a href="/wiki/zaarvox-s-heart"><img src="/img/zaarvox.png" alt="Zaarvox's Heart"></a></td>
          <td>ST</td>
        </tr>
        <tr>
          <td><a href="/wiki/wretched-rags"><img src="/img/rags.png" alt="Wretched Rags"></a></td>
          <td>UT</td>
        </tr>
        <tr>
          <td><a href="/wiki/wizard">Wizard</a></td>
          <td><a href="/wiki/wizard-robe"><img src="/img/wizard-robe.png" alt="Wizard Robe"></a></td>
        </tr>
      </table>
    </body></html>
    """

    records = parse_items_html(html, default_item_type="Armor")
    by_id = {row.id: row for row in records}

    assert by_id["item-zaarvox-s-heart"].tier == "ST"
    assert by_id["item-wretched-rags"].tier == "UT"
    assert "item-wizard" not in by_id
    assert "item-wizard-robe" in by_id


def test_parse_items_html_expands_tiered_ring_bundle() -> None:
    html = """
    <html><body>
      <table>
        <tr>
          <td><a href="/wiki/wisdom-rings"><img src="/img/wisdom.gif" alt="Wisdom Rings"></a></td>
          <td>Some grouped entry</td>
        </tr>
      </table>
    </body></html>
    """

    records = parse_items_html(html, default_item_type="Ring")

    assert len(records) == 7
    assert {record.tier for record in records} == {f"T{i}" for i in range(1, 8)}
    assert records[0].name.endswith("(T1)")


def test_parse_items_html_reads_ut_st_from_named_sections() -> None:
    html = """
    <html><body>
      <a name="untiered-rings"></a>
      <table>
        <tr>
          <td><a href="/wiki/the-twilight-gemstone"><img src="/img/twilight.png" alt="The Twilight Gemstone"></a></td>
          <td>Ring</td>
        </tr>
      </table>
      <a name="set-rings"></a>
      <table>
        <tr>
          <td><a href="/wiki/yokai-amulet"><img src="/img/yokai.png" alt="Yokai Amulet"></a></td>
          <td>Ring</td>
        </tr>
      </table>
    </body></html>
    """

    records = parse_items_html(html, default_item_type="Ring")
    by_id = {row.id: row for row in records}

    assert by_id["item-the-twilight-gemstone"].tier == "UT"
    assert by_id["item-yokai-amulet"].tier == "ST"
