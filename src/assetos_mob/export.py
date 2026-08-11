"""Controlled minimum-disclosure export package."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sqlite3
import time

from . import auth


def controlled_export(db_path: str | Path, output_path: str | Path, *, actor: auth.ActorContext) -> dict:
    actor.require(auth.EXPORT)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        payload = {
            "control_reference": "AOS-HO-00001",
            "export_version": "mob-dev-0.1",
            "export_timestamp_epoch": int(time.time()),
            "assets": [dict(r) for r in conn.execute("SELECT * FROM asset_records_current")],
            "evidence_references": [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT evidence_ref, asset_uuid, evidence_type, original_or_derivative,
                           information_class, continuity_state, acceptance_state,
                           completeness_state
                    FROM evidence_references
                    """
                )
            ],
            "taxonomy_assignments": [
                dict(r) for r in conn.execute("SELECT * FROM taxonomy_assignments")
            ],
            "information_class_assignments": [
                dict(r) for r in conn.execute("SELECT * FROM information_class_assignments")
            ],
            "validation_records": [
                dict(r) for r in conn.execute("SELECT * FROM validation_records")
            ],
        }
    finally:
        conn.close()
    encoded = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    export_hash = hashlib.sha256(encoded).hexdigest()
    payload["integrity_hash"] = f"sha256:{export_hash}"
    output_path = Path(output_path)
    output_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    return {"path": str(output_path), "integrity_hash": payload["integrity_hash"]}
