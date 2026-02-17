from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")


@dataclass(frozen=True)
class AssetRecord:
    id: str
    source_url: str
    local_path: str
    checksum_sha256: str | None = None


@dataclass(frozen=True)
class ClassRecord:
    id: str
    name: str
    icon_url: str
    page_url: str


@dataclass(frozen=True)
class ItemRecord:
    id: str
    name: str
    icon_url: str
    page_url: str
    item_type: str | None = None
    tier: str | None = None


@dataclass(frozen=True)
class RequirementRule:
    id: str
    label: str
    required_items: list[str] = field(default_factory=list)
    required_classes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RequirementsDataset:
    generated_at: str
    source_urls: list[str]
    classes: list[ClassRecord]
    items: list[ItemRecord]
    assets: list[AssetRecord]
    requirements: list[RequirementRule]

    @classmethod
    def new(
        cls,
        source_urls: list[str],
        classes: list[ClassRecord],
        items: list[ItemRecord],
        assets: list[AssetRecord],
        requirements: list[RequirementRule],
    ) -> "RequirementsDataset":
        return cls(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_urls=source_urls,
            classes=classes,
            items=items,
            assets=assets,
            requirements=requirements,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "source_urls": self.source_urls,
            "classes": [asdict(record) for record in self.classes],
            "items": [asdict(record) for record in self.items],
            "assets": [asdict(record) for record in self.assets],
            "requirements": [asdict(record) for record in self.requirements],
        }


def validate_requirements_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "requirements" not in config or not isinstance(config["requirements"], list):
        errors.append("config.requirements must be a list")
        return errors

    for index, rule in enumerate(config["requirements"]):
        if not isinstance(rule, dict):
            errors.append(f"requirements[{index}] must be an object")
            continue
        for key in ("id", "label"):
            if key not in rule or not isinstance(rule[key], str) or not rule[key].strip():
                errors.append(f"requirements[{index}].{key} must be a non-empty string")
        for key in ("required_items", "required_classes"):
            if key in rule and not isinstance(rule[key], list):
                errors.append(f"requirements[{index}].{key} must be a list when provided")
    return errors


def requirement_rule_from_config(raw_rule: dict[str, Any]) -> RequirementRule:
    return RequirementRule(
        id=raw_rule["id"],
        label=raw_rule["label"],
        required_items=list(raw_rule.get("required_items", [])),
        required_classes=list(raw_rule.get("required_classes", [])),
    )
