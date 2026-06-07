from __future__ import annotations

import sqlite3
from pathlib import Path

from utils import backup_sqlite_to_s3


def test_main_skips_when_bucket_is_missing(capsys, monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_S3_BUCKET", "")
    monkeypatch.setattr("sys.argv", ["backup_sqlite_to_s3"])

    exit_code = backup_sqlite_to_s3.main()

    assert exit_code == 0
    assert "Skipping backup: missing S3 bucket" in capsys.readouterr().out


def test_creates_and_uploads_snapshot(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "products.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO products(name) VALUES ('apple')")
    conn.commit()
    conn.close()
    uploaded: dict[str, str] = {}

    def fake_upload(file_path: Path, bucket: str, key: str, region: str | None) -> None:
        uploaded["bucket"] = bucket
        uploaded["key"] = key
        uploaded["region"] = region or ""
        uploaded["name"] = file_path.name

    monkeypatch.setattr(backup_sqlite_to_s3, "_upload_to_s3", fake_upload)

    key = backup_sqlite_to_s3.backup_sqlite_to_s3(
        db_path=db_path,
        bucket="test-bucket",
        prefix="mall-navigator/sqlite",
        region="ap-southeast-1",
    )

    assert key == uploaded["key"]
    assert uploaded["bucket"] == "test-bucket"
    assert uploaded["region"] == "ap-southeast-1"
    assert uploaded["name"].startswith("products-")
