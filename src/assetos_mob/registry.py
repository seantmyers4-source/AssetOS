"""Development/test Registry service for AssetOS MOB."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
import uuid

from . import auth
from .db import connect, migrate
from .errors import ConflictError, NotFoundError, UncertainCommitError, ValidationError
from .identifiers import generate_candidate_asset_id, normalize_asset_id

VALID_EVIDENCE_STATES = {"original", "derivative", "working_copy", "redacted", "annotated", "export"}
VALID_PROVIDER_NAMESPACES = {"google_drive"}
VALID_LOCATOR_ANNOTATIONS = {"no_op_repair_attempt", "not_canonical_locator_transition"}
GOOGLE_DRIVE_OBJECT_ID = re.compile(r"^[A-Za-z0-9_-]+$")
VALID_CONTINUITY_STATES = {
    "available",
    "unavailable",
    "broken",
    "access_denied",
    "moved",
    "recovery_pending",
    "preservation_defect",
}
BLOCKING_VALIDATION_STATES = {"invalid", "conflict", "rejected", "review_required"}


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
        self._require_permission(actor, auth.RESERVATION, action="attempted_reserve", subject_id=asset_id)
        parts = normalize_asset_id(asset_id)
        with self.conn:
            existing = self.conn.execute(
                "SELECT * FROM asset_id_reservations WHERE request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                if existing["asset_id"] != parts.canonical:
                    self._audit_failed(actor, request_id, "reservation_idempotency_conflict", "asset_id_changed")
                    raise ConflictError("request_id is already bound to a different asset_id")
                if existing["intended_asset_key"] != intended_asset_key:
                    self._audit_failed(
                        actor,
                        request_id,
                        "reservation_idempotency_conflict",
                        "intended_asset_key_changed",
                    )
                    raise ConflictError("request_id is already bound to a different intended_asset_key")
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
                event_payload={"request_id": request_id, "state": "reserved", "result": "success"},
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
        self._require_permission(actor, auth.ASSIGNMENT, action="attempted_assignment", subject_id=asset_id)
        parts = normalize_asset_id(asset_id)
        if simulate_uncertain_commit:
            raise UncertainCommitError("simulated uncertain assignment commit")
        with self.conn:
            existing = self.conn.execute(
                "SELECT * FROM assets WHERE assignment_request_id = ?", (request_id,)
            ).fetchone()
            if existing:
                if existing["asset_id"] != parts.canonical:
                    self._audit_failed(actor, request_id, "assignment_idempotency_conflict", "asset_id_changed")
                    raise ConflictError("request_id is already assigned to a different asset_id")
                if existing["intended_asset_key"] != intended_asset_key:
                    self._audit_failed(
                        actor,
                        request_id,
                        "assignment_idempotency_conflict",
                        "intended_asset_key_changed",
                    )
                    raise ConflictError("request_id is already assigned to a different intended_asset_key")
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
                event_payload={"request_id": request_id, "asset_uuid": asset_uuid, "result": "success"},
            )
        return dict(
            self.conn.execute("SELECT * FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone()
        )

    def validate_asset(self, *, asset_uuid: str, actor: auth.ActorContext) -> dict:
        self._require_permission(actor, auth.VALIDATION, action="attempted_validation", subject_id=asset_uuid)
        with self.conn:
            self._require_asset(asset_uuid)
            asset = self.conn.execute("SELECT * FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone()
            if asset["record_state"] in {"rejected", "merged", "retired"}:
                raise ConflictError("asset state is not validatable")
            taxonomy = self.conn.execute(
                """
                SELECT tt.class, tt.category FROM taxonomy_assignments ta
                JOIN taxonomy_terms tt ON tt.taxonomy_ref = ta.taxonomy_ref
                WHERE ta.asset_uuid = ? AND ta.superseded_at IS NULL
                ORDER BY ta.recorded_time DESC LIMIT 1
                """,
                (asset_uuid,),
            ).fetchone()
            if not taxonomy or not taxonomy["class"] or not taxonomy["category"]:
                raise ValidationError("publication requires Class and Category")
            info = self.conn.execute(
                """
                SELECT information_class FROM information_class_assignments
                WHERE asset_uuid = ? AND superseded_at IS NULL
                ORDER BY recorded_time DESC LIMIT 1
                """,
                (asset_uuid,),
            ).fetchone()
            if not info:
                raise ValidationError("publication requires information class")
            self._require_information_class(info["information_class"])
            self.conn.execute(
                "UPDATE assets SET validation_state = 'valid' WHERE asset_uuid = ?", (asset_uuid,)
            )
            self.conn.execute(
                """
                UPDATE taxonomy_assignments SET assignment_state = 'verified'
                WHERE asset_uuid = ? AND superseded_at IS NULL
                """,
                (asset_uuid,),
            )
            self.conn.execute(
                """
                UPDATE information_class_assignments SET assignment_state = 'verified'
                WHERE asset_uuid = ? AND superseded_at IS NULL
                """,
                (asset_uuid,),
            )
            self.conn.execute(
                """
                INSERT INTO validation_records(
                    subject_type, subject_id, validation_type, validation_state,
                    details_json, actor, authority
                ) VALUES ('asset', ?, 'publication_prerequisite', 'valid', ?, ?, ?)
                """,
                (
                    asset_uuid,
                    json.dumps({"result": "valid"}, sort_keys=True),
                    actor.actor,
                    actor.authority,
                ),
            )
        return dict(self.conn.execute("SELECT * FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone())

    def publish_asset(self, *, asset_uuid: str, request_id: str, actor: auth.ActorContext) -> dict:
        self._require_permission(actor, auth.PUBLICATION, action="attempted_publication", subject_id=asset_uuid)
        with self.conn:
            asset = self.conn.execute("SELECT * FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone()
            if not asset:
                raise NotFoundError("asset not found")
            if asset["publication_state"] == "published":
                self._audit(
                    "publication",
                    actor,
                    subject_id=asset_uuid,
                    event_payload={"request_id": request_id, "result": "idempotent_already_published"},
                )
                return dict(asset)
            blockers = self._publication_blockers(asset)
            if blockers:
                self._audit(
                    "failed_access",
                    actor,
                    subject_id=asset_uuid,
                    event_payload={
                        "action": "publication_prerequisite_check",
                        "result": "blocked",
                        "blockers": blockers,
                    },
                )
                self.conn.commit()
                raise ConflictError("publication prerequisites unsatisfied: " + ", ".join(blockers))
            self.conn.execute(
                """
                UPDATE assets
                SET publication_state = 'published', record_state = 'active'
                WHERE asset_uuid = ?
                """,
                (asset_uuid,),
            )
            assertion_id = self._append_assertion(
                asset_uuid=asset_uuid,
                assertion_type="publication",
                payload={"publication_state": "published", "request_id": request_id},
                actor=actor,
                reason="controlled synthetic publication",
                change_kind="genuine_change",
            )
            self._audit(
                "publication",
                actor,
                subject_id=asset_uuid,
                event_payload={
                    "request_id": request_id,
                    "assertion_id": assertion_id,
                    "result": "success",
                },
            )
        return dict(self.conn.execute("SELECT * FROM assets WHERE asset_uuid = ?", (asset_uuid,)).fetchone())

    def add_evidence_reference(
        self,
        *,
        asset_uuid: str,
        evidence_ref: str,
        evidence_type: str,
        drive_locator: str | None,
        information_class: str,
        original_or_derivative: str,
        continuity_state: str,
        acceptance_state: str,
        completeness_state: str,
        provenance: dict,
        actor: auth.ActorContext,
        provider_namespace: str | None = None,
        provider_object_id: str | None = None,
        canonical_locator: str | None = None,
        display_name: str | None = None,
    ) -> dict:
        self._require_permission(
            actor,
            auth.EVIDENCE_REFERENCE_ACCESS,
            action="attempted_evidence_reference_access",
            subject_id=evidence_ref,
        )
        self._require_information_class(information_class)
        self._require_evidence_state(original_or_derivative)
        self._validate_provider_identity(
            provider_namespace=provider_namespace,
            provider_object_id=provider_object_id,
            canonical_locator=canonical_locator,
        )
        if continuity_state not in VALID_CONTINUITY_STATES:
            raise ValidationError("invalid continuity_state")
        with self.conn:
            self._require_asset(asset_uuid)
            self.conn.execute(
                """
                INSERT INTO evidence_references(
                    evidence_ref, asset_uuid, evidence_type, drive_locator, original_or_derivative,
                    information_class, provenance_json, continuity_state, acceptance_state,
                    completeness_state, actor, authority, provider_namespace, provider_object_id,
                    canonical_locator, display_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_ref,
                    asset_uuid,
                    evidence_type,
                    drive_locator,
                    original_or_derivative,
                    information_class,
                    json.dumps(provenance, sort_keys=True),
                    continuity_state,
                    acceptance_state,
                    completeness_state,
                    actor.actor,
                    actor.authority,
                    provider_namespace,
                    provider_object_id,
                    canonical_locator,
                    display_name,
                ),
            )
            self.conn.execute(
                """
                INSERT INTO evidence_state_history(
                    evidence_ref, prior_original_or_derivative, new_original_or_derivative,
                    actor, authority, reason
                ) VALUES (?, NULL, ?, ?, ?, ?)
                """,
                (evidence_ref, original_or_derivative, actor.actor, actor.authority, "initial explicit evidence state"),
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

    def repair_evidence_locator(
        self,
        *,
        evidence_ref: str,
        new_drive_locator: str,
        continuity_state: str,
        reason: str,
        actor: auth.ActorContext,
        provider_namespace: str | None = None,
        provider_object_id: str | None = None,
    ) -> dict:
        self._require_permission(
            actor,
            auth.EVIDENCE_REFERENCE_ACCESS,
            action="attempted_evidence_locator_repair",
            subject_id=evidence_ref,
        )
        if continuity_state not in VALID_CONTINUITY_STATES:
            raise ValidationError("invalid continuity_state")
        with self.conn:
            current = self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
            if not current:
                raise NotFoundError("evidence reference not found")
            if current["drive_locator"] == new_drive_locator:
                raise ValidationError("no-op locator repair is not a canonical locator transition")
            self._require_provider_reconciliation(
                current,
                new_drive_locator=new_drive_locator,
                provider_namespace=provider_namespace,
                provider_object_id=provider_object_id,
            )
            self.conn.execute(
                """
                INSERT INTO evidence_locator_history(
                    evidence_ref, prior_drive_locator, new_drive_locator,
                    continuity_state, actor, authority, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_ref,
                    current["drive_locator"],
                    new_drive_locator,
                    continuity_state,
                    actor.actor,
                    actor.authority,
                    reason,
                ),
            )
            if current["provider_namespace"]:
                self.conn.execute(
                    """
                    UPDATE evidence_references
                    SET drive_locator = ?, canonical_locator = ?, continuity_state = ?
                    WHERE evidence_ref = ?
                    """,
                    (new_drive_locator, new_drive_locator, continuity_state, evidence_ref),
                )
            else:
                self.conn.execute(
                    "UPDATE evidence_references SET drive_locator = ?, continuity_state = ? WHERE evidence_ref = ?",
                    (new_drive_locator, continuity_state, evidence_ref),
                )
            self._audit(
                "evidence_reference_access",
                actor,
                subject_id=evidence_ref,
                event_payload={"action": "locator_repair", "result": "success"},
            )
        return dict(
            self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
        )

    def set_evidence_provider_identity(
        self,
        *,
        evidence_ref: str,
        provider_namespace: str,
        provider_object_id: str,
        canonical_locator: str,
        display_name: str | None,
        reason: str,
        actor: auth.ActorContext,
    ) -> dict:
        self._require_permission(
            actor,
            auth.EVIDENCE_REFERENCE_ACCESS,
            action="attempted_provider_identity_reconciliation",
            subject_id=evidence_ref,
        )
        self._validate_provider_identity(
            provider_namespace=provider_namespace,
            provider_object_id=provider_object_id,
            canonical_locator=canonical_locator,
        )
        with self.conn:
            current = self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
            if not current:
                raise NotFoundError("evidence reference not found")
            if current["provider_namespace"] and current["provider_namespace"] != provider_namespace:
                raise ConflictError("provider namespace mismatch")
            if current["provider_object_id"] and current["provider_object_id"] != provider_object_id:
                raise ConflictError("provider object identity mismatch")
            self.conn.execute(
                """
                UPDATE evidence_references
                SET provider_namespace = ?, provider_object_id = ?,
                    canonical_locator = ?, display_name = ?
                WHERE evidence_ref = ?
                """,
                (provider_namespace, provider_object_id, canonical_locator, display_name, evidence_ref),
            )
            self._audit(
                "evidence_reference_access",
                actor,
                subject_id=evidence_ref,
                event_payload={
                    "action": "provider_identity_reconciliation",
                    "result": "success",
                    "reason": reason,
                },
            )
        return dict(
            self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
        )

    def annotate_locator_history(
        self,
        *,
        locator_history_id: int,
        annotation_type: str,
        annotation: str,
        actor: auth.ActorContext,
    ) -> dict:
        self._require_permission(
            actor,
            auth.EVIDENCE_REFERENCE_ACCESS,
            action="attempted_locator_history_annotation",
            subject_id=str(locator_history_id),
        )
        if annotation_type not in VALID_LOCATOR_ANNOTATIONS:
            raise ValidationError("invalid locator annotation type")
        with self.conn:
            existing = self.conn.execute(
                "SELECT * FROM evidence_locator_history WHERE locator_history_id = ?",
                (locator_history_id,),
            ).fetchone()
            if not existing:
                raise NotFoundError("locator history event not found")
            cursor = self.conn.execute(
                """
                INSERT INTO evidence_locator_annotations(
                    locator_history_id, annotation_type, annotation, actor, authority
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (locator_history_id, annotation_type, annotation, actor.actor, actor.authority),
            )
            self._audit(
                "evidence_reference_access",
                actor,
                subject_id=str(locator_history_id),
                event_payload={"action": "locator_history_annotation", "result": "success"},
            )
        return dict(
            self.conn.execute(
                """
                SELECT * FROM evidence_locator_annotations
                WHERE locator_annotation_id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        )

    def set_evidence_state(
        self,
        *,
        evidence_ref: str,
        original_or_derivative: str,
        reason: str,
        actor: auth.ActorContext,
    ) -> dict:
        self._require_permission(
            actor,
            auth.EVIDENCE_REFERENCE_ACCESS,
            action="attempted_evidence_state_change",
            subject_id=evidence_ref,
        )
        self._require_evidence_state(original_or_derivative)
        with self.conn:
            current = self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
            if not current:
                raise NotFoundError("evidence reference not found")
            self.conn.execute(
                """
                INSERT INTO evidence_state_history(
                    evidence_ref, prior_original_or_derivative, new_original_or_derivative,
                    actor, authority, reason
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_ref,
                    current["original_or_derivative"],
                    original_or_derivative,
                    actor.actor,
                    actor.authority,
                    reason,
                ),
            )
            self.conn.execute(
                "UPDATE evidence_references SET original_or_derivative = ? WHERE evidence_ref = ?",
                (original_or_derivative, evidence_ref),
            )
            self._audit(
                "evidence_reference_access",
                actor,
                subject_id=evidence_ref,
                event_payload={"action": "evidence_state_change", "result": "success"},
            )
        return dict(
            self.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = ?", (evidence_ref,)
            ).fetchone()
        )

    def add_external_identifier(
        self,
        *,
        asset_uuid: str,
        identifier_type: str,
        normalized_value: str,
        display_value: str,
        issuer_namespace: str,
        information_class: str,
        actor: auth.ActorContext,
    ) -> dict:
        self._require_permission(actor, auth.VALIDATION, action="attempted_external_identifier", subject_id=asset_uuid)
        self._require_information_class(information_class)
        with self.conn:
            self._require_asset(asset_uuid)
            self.conn.execute(
                """
                INSERT INTO external_identifiers(
                    asset_uuid, identifier_type, normalized_value, display_value,
                    issuer_namespace, information_class
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_uuid,
                    identifier_type,
                    normalized_value,
                    display_value,
                    issuer_namespace,
                    information_class,
                ),
            )
        return dict(
            self.conn.execute(
                """
                SELECT * FROM external_identifiers
                WHERE asset_uuid = ? AND identifier_type = ? AND normalized_value = ?
                """,
                (asset_uuid, identifier_type, normalized_value),
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
        self._require_permission(
            actor, auth.CORRECTION, action="attempted_correction_supersession", subject_id=asset_uuid
        )
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
                event_payload={"new_assertion_id": assertion_id, "result": "success"},
            )
            return assertion_id

    def lookup_asset_id(self, asset_id: str, *, actor: auth.ActorContext) -> dict:
        self._require_permission(actor, auth.READ, action="attempted_read", subject_id=asset_id)
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
        self._require_permission(actor, auth.READ, action="attempted_search", subject_id=query)
        rows = self.conn.execute(
            """
            SELECT DISTINCT arc.asset_id, arc.preferred_name, arc.record_state,
                   arc.validation_state, arc.publication_state
            FROM asset_records_current arc
            LEFT JOIN taxonomy_assignments ta ON ta.asset_uuid = arc.asset_uuid AND ta.superseded_at IS NULL
            LEFT JOIN taxonomy_terms tt ON tt.taxonomy_ref = ta.taxonomy_ref
            LEFT JOIN external_identifiers ei ON ei.asset_uuid = arc.asset_uuid AND ei.superseded_at IS NULL
            LEFT JOIN evidence_references er ON er.asset_uuid = arc.asset_uuid
            WHERE arc.preferred_name LIKE ?
               OR arc.description LIKE ?
               OR tt.class LIKE ?
               OR tt.category LIKE ?
               OR ta.taxonomy_ref LIKE ?
               OR ei.normalized_value LIKE ?
               OR ei.display_value LIKE ?
               OR er.evidence_ref LIKE ?
            ORDER BY preferred_name
            LIMIT 25
            """,
            tuple(f"%{query}%" for _ in range(8)),
        ).fetchall()
        return [dict(row) for row in rows]

    def _publication_blockers(self, asset: sqlite3.Row) -> list[str]:
        blockers: list[str] = []
        try:
            normalize_asset_id(asset["asset_id"])
        except ValidationError:
            blockers.append("invalid_asset_id")
        reservation = self.conn.execute(
            "SELECT * FROM asset_id_reservations WHERE asset_id = ?", (asset["asset_id"],)
        ).fetchone()
        if not reservation or reservation["state"] != "assigned":
            blockers.append("identity_not_assigned")
        if asset["record_state"] in {"rejected", "suspended", "retired", "merged"}:
            blockers.append("record_state_blocks_publication")
        if asset["validation_state"] != "valid":
            blockers.append("asset_not_validated")
        taxonomy = self.conn.execute(
            """
            SELECT tt.class, tt.category, ta.assignment_state
            FROM taxonomy_assignments ta
            JOIN taxonomy_terms tt ON tt.taxonomy_ref = ta.taxonomy_ref
            WHERE ta.asset_uuid = ? AND ta.superseded_at IS NULL
            ORDER BY ta.recorded_time DESC LIMIT 1
            """,
            (asset["asset_uuid"],),
        ).fetchone()
        if not taxonomy or not taxonomy["class"] or not taxonomy["category"]:
            blockers.append("missing_class_category")
        elif taxonomy["assignment_state"] != "verified":
            blockers.append("taxonomy_not_verified")
        info = self.conn.execute(
            """
            SELECT information_class, assignment_state FROM information_class_assignments
            WHERE asset_uuid = ? AND superseded_at IS NULL
            ORDER BY recorded_time DESC LIMIT 1
            """,
            (asset["asset_uuid"],),
        ).fetchone()
        if not info:
            blockers.append("missing_information_class")
        else:
            try:
                self._require_information_class(info["information_class"])
            except ValidationError:
                blockers.append("invalid_information_class")
            if info["assignment_state"] != "verified":
                blockers.append("information_class_not_verified")
        bad_validation = self.conn.execute(
            """
            SELECT validation_state FROM validation_records
            WHERE subject_id = ? AND validation_state IN ('invalid', 'conflict', 'rejected', 'review_required')
            LIMIT 1
            """,
            (asset["asset_uuid"],),
        ).fetchone()
        if bad_validation:
            blockers.append("blocking_validation_record")
        return blockers

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

    def _validate_provider_identity(
        self,
        *,
        provider_namespace: str | None,
        provider_object_id: str | None,
        canonical_locator: str | None,
    ) -> None:
        supplied = [provider_namespace, provider_object_id, canonical_locator]
        if any(value is not None for value in supplied) and not all(supplied):
            raise ValidationError("provider namespace, object id, and canonical locator must be supplied together")
        if provider_namespace is None:
            return
        if provider_namespace not in VALID_PROVIDER_NAMESPACES:
            raise ValidationError("invalid provider namespace")
        if provider_namespace == "google_drive":
            if not GOOGLE_DRIVE_OBJECT_ID.fullmatch(provider_object_id or ""):
                raise ValidationError("invalid Google Drive provider object id")
            expected = f"gdrive://file/{provider_object_id}"
            if canonical_locator != expected:
                raise ValidationError("canonical locator does not match provider object id")

    def _require_provider_reconciliation(
        self,
        current: sqlite3.Row,
        *,
        new_drive_locator: str,
        provider_namespace: str | None,
        provider_object_id: str | None,
    ) -> None:
        current_namespace = current["provider_namespace"]
        current_object_id = current["provider_object_id"]
        if current_namespace or current_object_id:
            if not provider_namespace or not provider_object_id:
                raise ValidationError("provider-connected locator repair requires provider identity reconciliation")
            if provider_namespace != current_namespace or provider_object_id != current_object_id:
                raise ValidationError("provider identity mismatch for locator repair")
            self._validate_provider_identity(
                provider_namespace=provider_namespace,
                provider_object_id=provider_object_id,
                canonical_locator=new_drive_locator,
            )
        elif provider_namespace or provider_object_id:
            raise ValidationError("provider identity must be reconciled before provider-connected locator repair")

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
                json.dumps(_safe_audit_payload(event_payload), sort_keys=True),
            ),
        )

    def _audit_failed(self, actor: auth.ActorContext, subject_id: str, action: str, reason: str) -> None:
        self._audit(
            "failed_access",
            actor,
            subject_id=subject_id,
            event_payload={"action": action, "reason": reason, "result": "conflict"},
        )
        self.conn.commit()

    def _require_permission(
        self,
        actor: auth.ActorContext,
        permission: str,
        *,
        action: str,
        subject_id: str | None,
    ) -> None:
        if not actor.can(permission):
            self._audit(
                "failed_access",
                actor,
                subject_id=subject_id,
                event_payload={
                    "action": action,
                    "required_permission": permission,
                    "result": "denied",
                },
            )
            self.conn.commit()
            raise auth.AuthorizationError(f"{actor.actor} lacks {permission}")

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

    def _require_evidence_state(self, original_or_derivative: str) -> None:
        if original_or_derivative not in VALID_EVIDENCE_STATES:
            raise ValidationError("invalid evidence original_or_derivative state")


def _safe_audit_payload(payload: dict) -> dict:
    forbidden = {"password", "passphrase", "api_key", "apikey", "token", "bearer", "private_key", "secret"}
    safe = {}
    for key, value in payload.items():
        lower = key.lower()
        if any(term in lower for term in forbidden):
            safe[key] = "[redacted]"
        elif isinstance(value, dict):
            safe[key] = _safe_audit_payload(value)
        else:
            safe[key] = value
    return safe


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
