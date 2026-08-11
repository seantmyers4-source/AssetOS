"""Development/test Registry service for AssetOS MOB."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import uuid

from . import auth
from .db import connect, migrate
from .errors import ConflictError, NotFoundError, UncertainCommitError, ValidationError
from .identifiers import generate_candidate_asset_id, normalize_asset_id


class AssetOSRegistry:
    """Application-mediated SQLite Registry access for synthetic MOB testing."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.conn = connect(self.database_path)
        migrate(self.conn)
        seed_reference_data(self.conn)

    def close(self) -> None:
        self.conn.close()

    def generate_candidate(self) -> str:
        return generate_candidate_asset_id().canonical

    def reserve_asset_id(
        self,
        asset_id: str,
        *,
        request_id: str,
        intended_asset_key: str,
        actor: auth.ActorContext,
    ) -> dict:
        actor.require(auth.RESERVATION)
        parts = normalize_asset_id(asset_id)
        with self.conn:
            existing = self.conn.execute(
                "SELECT * FROM asset_id_reservations WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                if existing["asset_id"] != parts.canonical:
                    raise ConflictError("request_id is already bound to a different asset_id")
                return dict(existing)
            row = self.conn.execute(
                "SELECT * FROM asset_id_reservations WHERE asset_id = ?", (parts.canonical,)
            ).fetchone()
            if row and row["state"] in {"reserved", "assigned", "protected"}:
                raise ConflictError("asset_id is already reserved or protected")
            self.conn.execute(
                """
                INSERT INTO asset_id_reservations(
                    asset_id, body, check_symbol, state, request_id, intended_asset_key,
                    reserved_by, reserved_authority
                ) VALUES (?, ?, ?, 'reserved', ?, ?, ?, ?)
                """,
                (
                    parts.canonical,
                    parts.body,
                    parts.check_symbol,
                    request_id,
                    intended_asset_key,
                    actor.actor,
                    actor.authority,
                ),
            )
            self._audit(
                "asset_id_reservation",
                actor,
                subject_id=parts.canonical,
                event_payload={"request_id": request_id, "state": "reserved"},
            )
        return dict(
            self.conn.execute(
                "SELECT * FROM asset_id_reservations WHERE asset_id = ?", (parts.canonical,)
            ).fetchone()
        )

    def assign_asset(
        self,
        *,
        asset_id: str,
        request_id: str,
        intended_asset_key: str,
        preferred_name: str,
        description: str,
        taxonomy_ref: str,
        information_class: str,
        actor: auth.ActorContext,
        simulate_uncertain_commit: bool = False,
    ) -> dict:
        actor.require(auth.ASSIGNMENT)
        parts = normalize_asset_id(asset_id)
        if simulate_uncertain_commit:
            raise UncertainCommitError("simulated uncertain assignment commit")
        with self.conn:
            existing = self.conn.execute(
                "SELECT * FROM assets WHERE assignment_request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                if existing["asset_id"] != parts.canonical:
                    raise ConflictError("request_id is already assigned to a different asset_id")
                return dict(existing)
            reservation = self.conn.execute(
                "SELECT * FROM asset_id_reservations WHERE asset_id = ?", (parts.canonical,)
            ).fetchone()
            if not reservation:
                raise ConflictError("assignment requires a valid reservation")
            if reservation["request_id"] != request_id:
                raise ConflictError("reservation request_id mismatch")
            if reservation["intended_asset_key"] != intended_asset_key:
                raise ConflictError("reservation intended_asset_key mismatch")
            if reservation["state"] != "reserved":
                raise ConflictError("reservation is not assignable")
            self._require_taxonomy_ref(taxonomy_ref)
            self._require_information_class(information_class)
            asset_uuid = str(uuid.uuid4())
            self.conn.execute(
                """
                INSERT INTO assets(
                    asset_uuid, asset_id, assignment_request_id, intended_asset_key,
                    preferred_name, description, record_state, validation_state,
                    publication_state, created_by, created_authority
                ) VALUES (?, ?, ?, ?, ?, ?, 'draft', 'pending', 'unpublished', ?, ?)
                """,
                (
                    asset_uuid,
                    parts.canonical,
                    request_id,
                    intended_asset_key,
                    preferred_name,
                    description,
                    actor.actor,
                    actor.authority,
                ),
            )
            self.conn.execute(
                """
                UPDATE asset_id_reservations
                SET state = 'assigned', assigned_asset_uuid = ?, assigned_at = CURRENT_TIMESTAMP
                WHERE asset_id = ?
                """,
                (asset_uuid, parts.canonical),
            )
            self._append_assertion(
                asset_uuid=asset_uuid,
                assertion_type="canonical_record",
                payload={
                    "preferred_name": preferred_name,
                    "description": description,
                    "taxonomy_ref": taxonomy_ref,
                    "information_class": information_class,
                },
                actor=actor,
                reason="initial synthetic canonical assignment",
                change_kind="genuine_change",
            )
            self.conn.execute(
                """
                INSERT INTO taxonomy_assignments(
                    asset_uuid, taxonomy_ref, assignment_state, actor, authority, reason
                ) VALUES (?, ?, 'proposed', ?, ?, ?)
                """,
                (asset_uuid, taxonomy_ref, actor.actor, actor.authority, "synthetic intake"),
            )
            self.conn.execute(
                """
                INSERT INTO information_class_assignments(
                    asset_uuid, information_class, assignment_state, actor, authority, reason
                ) VALUES (?, ?, 'proposed', ?, ?, ?)
                """,
                (asset_uuid, information_class, actor.actor, actor.authority, "synthetic intake"),
            )
            self._audit(
                "permanent_assignment",
                actor,
                subject_id=parts.canonical,
                event_payload={"request_id": request_id, "asset_uuid": asset_uuid},
            )
        return dict(
            self.conn.execute("SELECT * FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone()
        )

    def add_evidence_reference(
        self,
        *,
        asset_uuid: str,
        evidence_ref: str,
        evidence_type: str,
        drive_locator: str | None,
        information_class: str,
        continuity_state: str,
        acceptance_state: str,
        completeness_state: str,
        provenance: dict,
        actor: auth.ActorContext,
    ) -> dict:
        actor.require(auth.EVIDENCE_REFERENCE_ACCESS)
        self._require_information_class(information_class)
        with self.conn:
            self._require_asset(asset_uuid)
            self.conn.execute(
                """
                INSERT INTO evidence_references(
                    evidence_ref, asset_uuid, evidence_type, drive_locator, original_or_derivative,
                    information_class, provenance_json, continuity_state, acceptance_state,
                    completeness_state, actor, authority
                ) VALUES (?, ?, ?, ?, 'original', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_ref,
                    asset_uuid,
                    evidence_type,
                    drive_locator,
                    information_class,
                    json.dumps(provenance, sort_keys=True),
                    continuity_state,
                    acceptance_state,
                    completeness_state,
                    actor.actor,
                    actor.authority,
                ),
            )
            self._audit(
                "evidence_reference_access",
                actor,
                subject_id=evidence_ref,
                event_payload={"asset_uuid": asset_uuid, "continuity_state": continuity_state},
            )
        return dict(
            self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
        )

    def supersede_canonical_assertion(
        self,
        *,
        asset_uuid: str,
        payload: dict,
        reason: str,
        change_kind: str,
        actor: auth.ActorContext,
    ) -> str:
        actor.require(auth.CORRECTION)
        with self.conn:
            current = self.conn.execute(
                """
                SELECT assertion_id FROM asset_assertions
                WHERE asset_uuid = ? AND assertion_type = 'canonical_record'
                  AND superseded_at IS NULL
                ORDER BY recorded_time DESC LIMIT 1
                """,
                (asset_uuid,),
            ).fetchone()
            if not current:
                raise NotFoundError("no active canonical assertion to supersede")
            self.conn.execute(
                "UPDATE asset_assertions SET superseded_at = CURRENT_TIMESTAMP WHERE assertion_id = ?",
                (current["assertion_id"],),
            )
            assertion_id = self._append_assertion(
                asset_uuid=asset_uuid,
                assertion_type="canonical_record",
                payload=payload,
                actor=actor,
                reason=reason,
                change_kind=change_kind,
                supersedes_assertion_id=current["assertion_id"],
            )
            self._audit(
                "correction_supersession",
                actor,
                subject_id=asset_uuid,
                event_payload={"new_assertion_id": assertion_id},
            )
            return assertion_id

    def lookup_asset_id(self, asset_id: str, *, actor: auth.ActorContext) -> dict:
        actor.require(auth.READ)
        parts = normalize_asset_id(asset_id)
        row = self.conn.execute(
            "SELECT * FROM asset_records_current WHERE asset_id = ?", (parts.canonical,)
        ).fetchone()
        if not row:
            reservation = self.conn.execute(
                "SELECT state FROM asset_id_reservations WHERE asset_id = ?", (parts.canonical,)
            ).fetchone()
            if reservation:
                raise NotFoundError("asset_id is syntactically valid but unissued")
            raise NotFoundError("asset_id not found")
        return dict(row)

    def limited_search(self, query: str, *, actor: auth.ActorContext) -> list[dict]:
        actor.require(auth.READ)
        rows = self.conn.execute(
            """
            SELECT asset_id, preferred_name, record_state, validation_state, publication_state
            FROM asset_records_current
            WHERE preferred_name LIKE ? OR description LIKE ?
            ORDER BY preferred_name
            LIMIT 25
            """,
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [dict(row) for row in rows]

    def _append_assertion(
        self,
        *,
        asset_uuid: str,
        assertion_type: str,
        payload: dict,
        actor: auth.ActorContext,
        reason: str,
        change_kind: str,
        supersedes_assertion_id: str | None = None,
    ) -> str:
        assertion_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO asset_assertions(
                assertion_id, asset_uuid, assertion_type, payload_json, actor, authority,
                reason, change_kind, dispute_state, supersedes_assertion_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'none', ?)
            """,
            (
                assertion_id,
                asset_uuid,
                assertion_type,
                json.dumps(payload, sort_keys=True),
                actor.actor,
                actor.authority,
                reason,
                change_kind,
                supersedes_assertion_id,
            ),
        )
        return assertion_id

    def _audit(
        self,
        event_type: str,
        actor: auth.ActorContext,
        *,
        subject_id: str | None,
        event_payload: dict,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO audit_events(event_type, actor, authority, subject_id, event_payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_type,
                actor.actor,
                actor.authority,
                subject_id,
                json.dumps(event_payload, sort_keys=True),
            ),
        )

    def _require_asset(self, asset_uuid: str) -> None:
        if not self.conn.execute("SELECT 1 FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone():
            raise NotFoundError("asset not found")

    def _require_taxonomy_ref(self, taxonomy_ref: str) -> None:
        if not self.conn.execute(
            "SELECT 1 FROM taxonomy_terms WHERE taxonomy_ref = ?", (taxonomy_ref,)
        ).fetchone():
            raise ValidationError("invalid taxonomy_ref")

    def _require_information_class(self, information_class: str) -> None:
        if not self.conn.execute(
            "SELECT 1 FROM information_classes WHERE information_class = ?", (information_class,)
        ).fetchone():
            raise ValidationError("invalid information_class")


def seed_reference_data(conn: sqlite3.Connection) -> None:
    with conn:
        for info_class in ("Public", "Personal", "Confidential", "Restricted"):
            conn.execute(
                "INSERT OR IGNORE INTO information_classes(information_class) VALUES (?)",
                (info_class,),
            )
        terms = [
            ("tax:physical:tools", "Asset", "Physical", "Tools", None, None),
            ("tax:physical:vehicle", "Asset", "Physical", "Vehicle", None, None),
            ("tax:physical:appliance", "Asset", "Physical", "Appliance", None, None),
            ("tax:intangible:document", "Asset", "Intangible", "Document", None, None),
            ("tax:intangible:warranty", "Asset", "Intangible", "Warranty", None, None),
        ]
        for term in terms:
            conn.execute(
                """
                INSERT OR IGNORE INTO taxonomy_terms(
                    taxonomy_ref, root, class, category, subcategory, type
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                term,
            )
