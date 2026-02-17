from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from src.models.schema import AssetRecord


class AssetValidationError(RuntimeError):
    pass


def download_assets(records: list[dict], output_dir: Path) -> list[AssetRecord]:
    output_dir.mkdir(parents=True, exist_ok=True)
    assets: list[AssetRecord] = []

    for record in records:
        entity_id = record["id"]
        source_url = record["icon_url"]
        ext = _guess_extension(source_url)
        local_path = output_dir / f"{entity_id}.{ext}"

        request = Request(source_url, headers={"User-Agent": "realm-requirements-sheet-bot/0.1"})
        with urlopen(request, timeout=30) as response:
            content = response.read()
        local_path.write_bytes(content)

        checksum = hashlib.sha256(content).hexdigest()
        assets.append(
            AssetRecord(
                id=entity_id,
                source_url=source_url,
                local_path=str(local_path),
                checksum_sha256=checksum,
            )
        )

    return assets


def validate_assets(records: list[dict], assets: list[AssetRecord], report_path: Path) -> dict:
    by_id = {asset.id: asset for asset in assets}
    missing: list[str] = []
    corrupt: list[str] = []

    for record in records:
        entity_id = record["id"]
        asset = by_id.get(entity_id)
        if not asset:
            missing.append(entity_id)
            continue

        image_path = Path(asset.local_path)
        if not image_path.exists():
            missing.append(entity_id)
            continue

        if not _is_supported_image(image_path):
            corrupt.append(entity_id)

    reverse_checksums: dict[str, list[str]] = {}
    for asset in assets:
        reverse_checksums.setdefault(asset.checksum_sha256 or "", []).append(asset.id)

    duplicates = {checksum: ids for checksum, ids in reverse_checksums.items() if checksum and len(ids) > 1}

    report = {
        "missing": sorted(missing),
        "corrupt": sorted(corrupt),
        "duplicates": duplicates,
        "asset_count": len(assets),
        "record_count": len(records),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if missing or corrupt:
        raise AssetValidationError(
            f"Asset validation failed with {len(missing)} missing and {len(corrupt)} corrupt assets"
        )

    return report


def _guess_extension(url: str) -> str:
    lowered = url.lower().split("?")[0]
    for ext in ("png", "jpg", "jpeg", "gif", "webp"):
        if lowered.endswith(f".{ext}"):
            return "jpg" if ext == "jpeg" else ext
    return "png"


def _is_supported_image(image_path: Path) -> bool:
    """Detect image files via magic bytes.

    Python 3.13 removed ``imghdr`` from the stdlib, so we validate using
    lightweight signature checks for the formats we download.
    """

    try:
        header = image_path.read_bytes()[:16]
    except OSError:
        return False

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    if header.startswith(b"\xff\xd8\xff"):
        return True

    if header.startswith((b"GIF87a", b"GIF89a")):
        return True

    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return True

    return False
