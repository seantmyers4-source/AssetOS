"""Controlled minimum-disclosure export package."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sqlite3
import time

from . import auth


def controlled_export(
    db_path: str | Path,
    output_path: str | Path,
    *,
    actor: auth.ActorContext,
    allowed_information_classes: set[str] | None = None,
    purpose: str = "synthetic-release-readiness-test",
    include_restricted_details: bool = False,
) -> dict:
    allowed_information_classes = allowed_information_classes or {"Public"}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if not actor.can(auth.EXPORT):
            _audit(
                conn,
                "failed_access",
                actor,
                subject_id="controlled_export",
                event_payload={
                    "action": "attempted_export",
                    "required_permission": auth.EXPORT,
                    "result": "denied",
                },
            )
            conn.commit()
            raise auth.AuthorizationError(f"{actor.actor} lacks {auth.EXPORT}")
        payload = {
            "control_reference": "AOS-HO-00001",
            "export_version": "mob-dev-0.2",
            "export_timestamp_epoch": int(time.time()),
            "purpose": purpose,
            "minimum_disclosure_profile": {
                "allowed_information_classes": sorted(allowed_information_classes),
                "include_restricted_details": include_restricted_details,
            },
            "assets": _export_assets(conn, allowed_information_classes, include_restricted_details),
            "evidence_references": _export_evidence(
                conn, allowed_information_classes, include_restricted_details
            ),
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
        encoded_without_hash = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
        export_hash = hashlib.sha256(encoded_without_hash).hexdigest()
        payload["integrity_hash"] = f"sha256:{export_hash}"
        output_path = Path(output_path)
        output_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        conn.execute(
            """
            INSERT INTO controlled_exports(
                export_version, integrity_hash, minimum_disclosure_profile, actor, authority
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["export_version"],
                payload["integrity_hash"],
                json.dumps(payload["minimum_disclosure_profile"], sort_keys=True),
                actor.actor,
                actor.authority,
            ),
        )
        _audit(
            conn,
            "export",
            actor,
            subject_id=output_path.name,
            event_payload={
                "action": "export",
                "result": "success",
                "purpose": purpose,
                "integrity_hash": payload["integrity_hash"],
            },
        )
        conn.commit()
        return {"path": str(output_path), "integrity_hash": payload["integrity_hash"]}
    finally:
        conn.close()


def _export_assets(
    conn: sqlite3.Connection,
    allowed_information_classes: set[str],
    include_restricted_details: bool,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT arc.*, ica.information_class
        FROM asset_records_current arc
        JOIN information_class_assignments ica
          ON ica.asset_uuid = arc.asset_uuid AND ica.superseded_at IS NULL
        """
    ).fetchall()
    exported = []
    for row in rows:
        info_class = row["information_class"]
        include_details = info_class in allowed_information_classes and (
            info_class != "Restricted" or include_restricted_details
        )
        item = {
            "asset_uuid": row["asset_uuid"],
            "asset_id": row["asset_id"],
            "preferred_name": row["preferred_name"],
            "information_class": info_class,
            "record_state": row["record_state"],
            "validation_state": row["validation_state"],
            "publication_state": row["publication_state"],
        }
        if include_details:
            item["description"] = row["description"]
            item["current_payload_json"] = row["current_payload_json"]
        else:
            item["description"] = "[suppressed]"
            item["current_payload_json"] = "[suppressed]"
        item["external_identifiers"] = _export_external_identifiers(
            conn, row["asset_uuid"], allowed_information_classes, include_restricted_details
        )
        exported.append(item)
    return exported


def _export_external_identifiers(
    conn: sqlite3.Connection,
    asset_uuid: str,
    allowed_information_classes: set[str],
    include_restricted_details: bool,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT identifier_type, normalized_value, display_value, issuer_namespace, information_class
        FROM external_identifiers
        WHERE asset_uuid = ? AND superseded_at IS NULL
        """,
        (asset_uuid,),
    ).fetchall()
    exported = []
    for row in rows:
        include_details = row["information_class"] in allowed_information_classes and (
            row["information_class"] != "Restricted" or include_restricted_details
        )
        exported.append(
            {
                "identifier_type": row["identifier_type"],
                "issuer_namespace": row["issuer_namespace"],
                "information_class": row["information_class"],
                "normalized_value": row["normalized_value"] if include_details else "[suppressed]",
                "display_value": row["display_value"] if include_details else "[suppressed]",
            }
        )
    return exported


def _export_evidence(
    conn: sqlite3.Connection,
    allowed_information_classes: set[str],
    include_restricted_details: bool,
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT evidence_ref, asset_uuid, evidence_type, drive_locator, original_or_derivative,
               information_class, continuity_state, acceptance_state, completeness_state
        FROM evidence_references
        """
    ).fetchall()
    exported = []
    for row in rows:
        include_locator = row["information_class"] in allowed_information_classes and (
            row["information_class"] != "Restricted" or include_restricted_details
        )
        exported.append(
            {
                "evidence_ref": row["evidence_ref"],
                "asset_uuid": row["asset_uuid"],
                "evidence_type": row["evidence_type"],
                "original_or_derivative": row["original_or_derivative"],
                "information_class": row["information_class"],
                "continuity_state": row["continuity_state"],
                "acceptance_state": row["acceptance_state"],
                "completeness_state": row["completeness_state"],
                "drive_locator": row["drive_locator"] if include_locator else "[suppressed]",
            }
        )
    return exported


def _audit(
    conn: sqlite3.Connection,
    event_type: str,
    actor: auth.ActorContext,
    *,
    subject_id: str | None,
    event_payload: dict,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_events(event_type, actor, authority, subject_id, event_payload_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_type, actor.actor, actor.authority, subject_id, json.dumps(event_payload, sort_keys=True)),
    )
