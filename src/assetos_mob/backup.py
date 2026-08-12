"""SQLite-consistent encrypted backup and controlled restore helpers."""

from __future__ import annotations

from base64 import urlsafe_b64encode
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
import time

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from . import auth
from .errors import AssetOSError

KDF_ITERATIONS = 600_000
SALT_BYTES = 16


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
    source_db = Path(source_db)
    output_path = Path(output_path)
    if not actor.can(auth.BACKUP):
        _audit_to_db(
            source_db,
            "failed_access",
            actor,
            subject_id=source_db.name,
            event_payload={"action": "attempted_backup", "required_permission": auth.BACKUP, "result": "denied"},
        )
        raise auth.AuthorizationError(f"{actor.actor} lacks {auth.BACKUP}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        snapshot = tmp_path / "assetos-mob.sqlite"
        sqlite_consistent_snapshot(source_db, snapshot)
        digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        manifest = {
            "control_reference": "AOS-HO-00001",
            "backup_type": "sqlite-consistent-fernet-development",
            "encryption": {
                "algorithm": "Fernet AES-128-CBC with HMAC-SHA256",
                "kdf": "PBKDF2-HMAC-SHA256",
                "kdf_iterations": KDF_ITERATIONS,
                "salt_bytes": SALT_BYTES,
            },
            "source": source_db.name,
            "snapshot_sha256": digest,
            "created_at_epoch": int(time.time()),
            "actor": actor.actor,
            "authority": actor.authority,
        }
        (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tar_path = tmp_path / "backup.tar"
        with tarfile.open(tar_path, "w") as tar:
            tar.add(snapshot, arcname="assetos-mob.sqlite")
            tar.add(tmp_path / "manifest.json", arcname="manifest.json")
        salt = os.urandom(SALT_BYTES)
        token = _fernet(passphrase, salt).encrypt(tar_path.read_bytes())
        envelope = {
            "format": "assetos-mob-fernet-backup-v1",
            "salt_hex": salt.hex(),
            "kdf_iterations": KDF_ITERATIONS,
            "token": token.decode("ascii"),
        }
        output_path.write_text(json.dumps(envelope, sort_keys=True), encoding="utf-8")
        _audit_to_db(
            source_db,
            "backup",
            actor,
            subject_id=source_db.name,
            event_payload={
                "action": "backup",
                "result": "success",
                "output": output_path.name,
                "snapshot_sha256": digest,
            },
        )
        return manifest | {"encrypted_backup": str(output_path)}


def restore_encrypted_backup(
    encrypted_path: str | Path,
    restore_db_path: str | Path,
    *,
    passphrase: str,
    actor: auth.ActorContext,
) -> dict:
    encrypted_path = Path(encrypted_path)
    restore_db_path = Path(restore_db_path)
    if not actor.can(auth.RESTORE):
        raise auth.AuthorizationError(f"{actor.actor} lacks {auth.RESTORE}")
    try:
        envelope = json.loads(encrypted_path.read_text(encoding="utf-8"))
        salt = bytes.fromhex(envelope["salt_hex"])
        token = envelope["token"].encode("ascii")
        decrypted = _fernet(passphrase, salt).decrypt(token)
    except (KeyError, ValueError, InvalidToken) as exc:
        raise AssetOSError("encrypted backup could not be authenticated or decrypted") from exc
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tar_path = tmp_path / "backup.tar"
        tar_path.write_bytes(decrypted)
        with tarfile.open(tar_path, "r") as tar:
            _safe_extract(tar, tmp_path)
        snapshot = tmp_path / "assetos-mob.sqlite"
        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != manifest["snapshot_sha256"]:
            raise AssetOSError("restored backup failed integrity hash verification")
        shutil.copy2(snapshot, restore_db_path)
        _audit_to_db(
            restore_db_path,
            "restore",
            actor,
            subject_id=restore_db_path.name,
            event_payload={
                "action": "restore",
                "result": "success",
                "source_backup": encrypted_path.name,
                "snapshot_sha256": manifest["snapshot_sha256"],
            },
        )
        return manifest | {"restored_database": str(restore_db_path)}


def _fernet(passphrase: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return Fernet(urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8"))))


def _safe_extract(tar: tarfile.TarFile, destination: Path) -> None:
    for member in tar.getmembers():
        target = (destination / member.name).resolve()
        if not str(target).startswith(str(destination.resolve())):
            raise AssetOSError("backup archive contains unsafe path")
    tar.extractall(destination, filter="data")


def _audit_to_db(
    db_path: Path,
    event_type: str,
    actor: auth.ActorContext,
    *,
    subject_id: str | None,
    event_payload: dict,
) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO audit_events(event_type, actor, authority, subject_id, event_payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, actor.actor, actor.authority, subject_id, json.dumps(event_payload, sort_keys=True)),
        )
        conn.commit()
    finally:
        conn.close()
