from src.scraper.assets import _sniff_image_type


def test_sniff_image_type_known_signatures() -> None:
    assert _sniff_image_type(b"\x89PNG\r\n\x1a\nxxxx") == "png"
    assert _sniff_image_type(b"\xff\xd8\xff\xe0xxxx") == "jpeg"
    assert _sniff_image_type(b"GIF89axxxx") == "gif"
    assert _sniff_image_type(b"RIFFxxxxWEBPxxxx") == "webp"


def test_sniff_image_type_unknown_signature() -> None:
    assert _sniff_image_type(b"not-an-image") is None
