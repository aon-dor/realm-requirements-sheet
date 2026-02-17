# realm-requirements-sheet

Config-driven data pipeline for a Realm of the Mad God requirements sheet.

## Project structure

- `src/scraper/`: RealmEye scraping and asset tooling.
- `src/models/`: normalized data models and config validation.
- `config/requirements-sheet.yaml`: requirement rules consumed by dataset builder.
- `data/raw/`: HTML snapshots for parser debugging.
- `data/normalized/`: generated JSON artifacts for app consumption.
- `src/assets/`: downloaded item/class icons.

## Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the pipeline:

```bash
python -m src.cli scrape-classes
python -m src.cli scrape-items
python -m src.cli download-assets
python -m src.cli validate-assets
python -m src.cli build-dataset
```

Outputs:

- `data/normalized/classes.json`
- `data/normalized/items.json`
- `data/normalized/assets.json`
- `data/normalized/asset-validation.json`
- `data/normalized/requirements-dataset.json`

## Notes

- HTTP requests use retry/backoff and a polite delay.
- Parsers store raw HTML snapshots for easier break/fix when RealmEye markup changes.
- Config validation fails fast when required rule keys are missing.


### Network note

If your environment has a restrictive proxy, you can try bypassing proxy env variables:

```bash
REALMEYE_DISABLE_PROXY=1 python -m src.cli scrape-classes
```

If direct egress is not allowed, live scraping will still fail and you can continue parser development with fixtures.
