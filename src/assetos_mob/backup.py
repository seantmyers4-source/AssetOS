"""SQLite-consistent encrypted backup and controlled restore helpers."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil
import sqlite3
import subprocess
import tempfile
import time

from . import auth
from .errors import AssetOSError


def sqlite_consistent_snapshot(source_db: str | Path, snapshot_path: str | Path) -> None:
    source = sqlite3.connect(source_db)
    target = sqlite3.connect(snapshot_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def encrypted_backup(
    source_db: str | Path,
    output_path: str | Path,
    *,
    passphrase: str,
    actor: auth.ActorContext,
) -> dict:
    actor.require(auth.BACKUP)
    if not shutil.which("openssl"):
        raise AssetOSError("openssl is required for encrypted backup in this development package")
    source_db = Path(source_db)
    output_path = Path(output_path)
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / "assetos-mob.sqlite"
        sqlite_consistent_snapshot(source_db, snapshot)
        digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        manifest = {
            "control_reference": "AOS-HO-00001",
            "backup_type": "sqlite-consistent-encrypted-development",
            "source": source_db.name,
            "snapshot_sha256": digest,
            "created_at_epoch": int(time.time()),
            "actor": actor.actor,
            "authority": actor.authority,
        }
        (Path(tmp) / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tar_path = Path(tmp) / "backup.tar"
        subprocess.run(
            ["tar", "-cf", str(tar_path), "-C", tmp, "assetos-mob.sqlite", "manifest.json"],
            check=True,
        )
        subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-256-cbc",
                "-pbkdf2",
                "-salt",
                "-pass",
                f"pass:{passphrase}",
                "-in",
                str(tar_path),
                "-out",
                str(output_path),
            ],
            check=True,
        )
        return manifest | {"encrypted_backup": str(output_path)}


def restore_encrypted_backup(
    encrypted_path: str | Path,
    restore_db_path: str | Path,
    *,
    passphrase: str,
    actor: auth.ActorContext,
) -> dict:
    actor.require(auth.RESTORE)
    if not shutil.which("openssl"):
        raise AssetOSError("openssl is required for encrypted restore in this development package")
    encrypted_path = Path(encrypted_path)
    restore_db_path = Path(restore_db_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tar_path = tmp / "backup.tar"
        subprocess.run(
            [
                "openssl",
                "enc",
                "-d",
                "-aes-256-cbc",
                "-pbkdf2",
                "-pass",
                f"pass:{passphrase}",
                "-in",
                str(encrypted_path),
                "-out",
                str(tar_path),
            ],
            check=True,
        )
        subprocess.run(["tar", "-xf", str(tar_path), "-C", str(tmp)], check=True)
        snapshot = tmp / "assetos-mob.sqlite"
        manifest = json.loads((tmp / "manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != manifest["snapshot_sha256"]:
            raise AssetOSError("restored backup failed integrity hash verification")
        shutil.copy2(snapshot, restore_db_path)
        return manifest | {"restored_database": str(restore_db_path)}
