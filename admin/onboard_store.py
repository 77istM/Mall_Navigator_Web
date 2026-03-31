"""One-click onboarding script for a new mall/store dataset.

Usage:
    python admin/onboard_store.py --store-id my_mall --name "My Mall" --lat 51.5 --lng -0.1
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utils.operator_tools import scaffold_store


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new mall data pack")
    parser.add_argument("--store-id", required=True, help="Unique store key (letters, numbers, underscore)")
    parser.add_argument("--name", required=True, help="Store display name")
    parser.add_argument("--lat", type=float, required=True, help="Store latitude")
    parser.add_argument("--lng", type=float, required=True, help="Store longitude")
    parser.add_argument("--template-store", default="demo", help="Existing store key used as scaffold source")
    parser.add_argument("--stores-path", default="data/stores.json")
    parser.add_argument("--output-root", default="data/stores")
    args = parser.parse_args()

    created = scaffold_store(
        store_id=args.store_id,
        store_name=args.name,
        lat=args.lat,
        lng=args.lng,
        template_store=args.template_store,
        stores_json_path=Path(args.stores_path),
        stores_root=Path(args.output_root),
    )

    print("Created store scaffold:")
    for path in created:
        print(f"- {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
