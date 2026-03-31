"""CLI script to migrate products JSON data into SQLite."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from utils.db import migrate_json_to_sqlite


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Migrate products.json to SQLite")
    parser.add_argument(
        "--json",
        default="data/products.json",
        help="Source JSON file path",
    )
    parser.add_argument(
        "--sqlite",
        default="data/products.db",
        help="Target SQLite DB file path",
    )
    args = parser.parse_args()

    migrated = migrate_json_to_sqlite(Path(args.json), Path(args.sqlite))
    logging.getLogger(__name__).info("Migrated %s products to %s", migrated, args.sqlite)


if __name__ == "__main__":
    main()
