from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path


from src.models.schema import (
    RequirementsDataset,
    requirement_rule_from_config,
    validate_requirements_config,
)
from src.scraper.assets import download_assets, validate_assets
from src.scraper.classes import CLASSES_PATH, parse_classes_html
from src.scraper.items import ITEMS_PATH, parse_items_html
from src.scraper.realmeye_client import RealmEyeClient

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
NORMALIZED_DIR = ROOT / "data" / "normalized"
CONFIG_PATH = ROOT / "config" / "requirements-sheet.yaml"


def scrape_classes(client: RealmEyeClient) -> list[dict]:
    html = client.fetch(CLASSES_PATH)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "classes.html").write_text(html, encoding="utf-8")

    classes = parse_classes_html(html, client.base_url)
    payload = [asdict(record) for record in classes]
    (NORMALIZED_DIR / "classes.json").parent.mkdir(parents=True, exist_ok=True)
    (NORMALIZED_DIR / "classes.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def scrape_items(client: RealmEyeClient) -> list[dict]:
    html = client.fetch(ITEMS_PATH)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "items.html").write_text(html, encoding="utf-8")

    items = parse_items_html(html, client.base_url)
    payload = [asdict(record) for record in items]
    (NORMALIZED_DIR / "items.json").parent.mkdir(parents=True, exist_ok=True)
    (NORMALIZED_DIR / "items.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_requirements() -> list:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    errors = validate_requirements_config(config)
    if errors:
        raise ValueError("Invalid config:\n - " + "\n - ".join(errors))
    return [requirement_rule_from_config(rule) for rule in config["requirements"]]


def build_dataset() -> dict:
    classes = json.loads((NORMALIZED_DIR / "classes.json").read_text(encoding="utf-8"))
    items = json.loads((NORMALIZED_DIR / "items.json").read_text(encoding="utf-8"))
    assets = json.loads((NORMALIZED_DIR / "assets.json").read_text(encoding="utf-8"))

    dataset = RequirementsDataset.new(
        source_urls=["https://www.realmeye.com/wiki/classes", "https://www.realmeye.com/wiki/items"],
        classes=[_dc_from_dict("class", row) for row in classes],
        items=[_dc_from_dict("item", row) for row in items],
        assets=[_dc_from_dict("asset", row) for row in assets],
        requirements=load_requirements(),
    )
    payload = dataset.to_dict()
    (NORMALIZED_DIR / "requirements-dataset.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _dc_from_dict(kind: str, row: dict):
    from src.models.schema import AssetRecord, ClassRecord, ItemRecord

    if kind == "class":
        return ClassRecord(**row)
    if kind == "item":
        return ItemRecord(**row)
    if kind == "asset":
        return AssetRecord(**row)
    raise ValueError(f"Unknown kind {kind}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Realm requirements sheet pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scrape-classes")
    sub.add_parser("scrape-items")
    sub.add_parser("download-assets")
    sub.add_parser("validate-assets")
    sub.add_parser("build-dataset")

    args = parser.parse_args()
    client = RealmEyeClient()

    if args.command == "scrape-classes":
        print(json.dumps(scrape_classes(client), indent=2))
        return
    if args.command == "scrape-items":
        print(json.dumps(scrape_items(client), indent=2))
        return

    if args.command == "download-assets":
        classes = json.loads((NORMALIZED_DIR / "classes.json").read_text(encoding="utf-8"))
        items = json.loads((NORMALIZED_DIR / "items.json").read_text(encoding="utf-8"))
        assets = download_assets(classes + items, ROOT / "src" / "assets")
        payload = [asdict(asset) for asset in assets]
        (NORMALIZED_DIR / "assets.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return

    if args.command == "validate-assets":
        classes = json.loads((NORMALIZED_DIR / "classes.json").read_text(encoding="utf-8"))
        items = json.loads((NORMALIZED_DIR / "items.json").read_text(encoding="utf-8"))
        assets_raw = json.loads((NORMALIZED_DIR / "assets.json").read_text(encoding="utf-8"))
        from src.models.schema import AssetRecord

        assets = [AssetRecord(**row) for row in assets_raw]
        report = validate_assets(classes + items, assets, NORMALIZED_DIR / "asset-validation.json")
        print(json.dumps(report, indent=2))
        return

    if args.command == "build-dataset":
        print(json.dumps(build_dataset(), indent=2))
        return


if __name__ == "__main__":
    main()
