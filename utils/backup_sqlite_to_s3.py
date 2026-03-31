"""Backup SQLite database snapshots to S3.

Usage:
    python -m utils.backup_sqlite_to_s3
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import tempfile
from pathlib import Path


def _upload_to_s3(file_path: Path, bucket: str, key: str, region: str | None) -> None:
    import boto3

    kwargs = {}
    if region:
        kwargs["region_name"] = region

    client = boto3.client("s3", **kwargs)
    client.upload_file(str(file_path), bucket, key)


def backup_sqlite_to_s3(db_path: Path, bucket: str, prefix: str, region: str | None = None) -> str:
    """Create a timestamped snapshot and upload it to S3.

    Returns the uploaded S3 key.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    timestamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_key = f"{prefix.rstrip('/')}/{db_path.stem}-{timestamp}.sqlite3"

    with tempfile.TemporaryDirectory(prefix="mallnav_backup_") as tmp_dir:
        snapshot_path = Path(tmp_dir) / f"{db_path.stem}-{timestamp}.sqlite3"
        shutil.copy2(db_path, snapshot_path)
        _upload_to_s3(snapshot_path, bucket=bucket, key=backup_key, region=region)

    return backup_key


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup a SQLite DB to S3")
    parser.add_argument("--db-path", default=os.getenv("SQLITE_DB_PATH", "data/products.db"))
    parser.add_argument("--bucket", default=os.getenv("BACKUP_S3_BUCKET", ""))
    parser.add_argument("--prefix", default=os.getenv("BACKUP_S3_PREFIX", "mall-navigator/sqlite"))
    parser.add_argument("--region", default=os.getenv("AWS_REGION", ""))
    args = parser.parse_args()

    if not args.bucket:
        raise ValueError("Missing S3 bucket. Set --bucket or BACKUP_S3_BUCKET.")

    key = backup_sqlite_to_s3(
        db_path=Path(args.db_path),
        bucket=args.bucket,
        prefix=args.prefix,
        region=args.region or None,
    )
    print(f"Uploaded backup to s3://{args.bucket}/{key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
