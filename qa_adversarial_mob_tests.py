import json
import sqlite3
import tempfile
from pathlib import Path
import unittest

import tests._bootstrap  # noqa: F401

from assetos_mob import auth
from assetos_mob.backup import encrypted_backup, restore_encrypted_backup
from assetos_mob.errors import AuthorizationError, ConflictError, ValidationError
from assetos_mob.export import controlled_export
from assetos_mob.registry import AssetOSRegistry
from tests.test_provider_locator_semantics import (
    ProviderLocatorSemanticsTests as _ProviderLocatorSemanticsTests,
    SyntheticV011MigrationTests as _SyntheticV011MigrationTests,
)


class MOBReleaseBlockingCorrections(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "mob.sqlite"
        self.registry = AssetOSRegistry(self.db_path)
        self.actor = auth.ENGINEERING_TEST_ACTOR

    def tearDown(self):
        self.registry.close()
        self.tmp.cleanup()

    def _assigned_asset(self, *, info_class="Personal", taxonomy_ref="tax:physical:tools", name="Synthetic"):
        asset_id = self.registry.generate_candidate()
        request_id = f"req-{name}-{info_class}".lower().replace(" ", "-")
        self.registry.reserve_asset_id(
            asset_id, request_id=request_id, intended_asset_key=request_id, actor=self.actor
        )
        return self.registry.assign_asset(
            asset_id=asset_id,
            request_id=request_id,
            intended_asset_key=request_id,
            preferred_name=name,
            description=f"{info_class} controlled description",
            taxonomy_ref=taxonomy_ref,
            information_class=info_class,
            actor=self.actor,
        )

    def test_publication_gate_blocks_incomplete_draft_and_publishes_valid_asset(self):
        asset = self._assigned_asset(name="Publish Gate")
        with self.assertRaises(ConflictError):
            self.registry.publish_asset(
                asset_uuid=asset["asset_uuid"], request_id="pub-1", actor=self.actor
            )
        self.registry.validate_asset(asset_uuid=asset["asset_uuid"], actor=self.actor)
        published = self.registry.publish_asset(
            asset_uuid=asset["asset_uuid"], request_id="pub-1", actor=self.actor
        )
        self.assertEqual("published", published["publication_state"])
        again = self.registry.publish_asset(
            asset_uuid=asset["asset_uuid"], request_id="pub-1", actor=self.actor
        )
        self.assertEqual("published", again["publication_state"])
        events = self.registry.conn.execute(
            "SELECT event_type FROM audit_events WHERE subject_id = ?", (asset["asset_uuid"],)
        ).fetchall()
        self.assertIn("publication", [row["event_type"] for row in events])
        self.assertIn("failed_access", [row["event_type"] for row in events])

    def test_publication_gate_blocks_conflict_validation_record(self):
        asset = self._assigned_asset(name="Conflict Publish")
        self.registry.validate_asset(asset_uuid=asset["asset_uuid"], actor=self.actor)
        self.registry.conn.execute(
            """
            INSERT INTO validation_records(
                subject_type, subject_id, validation_type, validation_state,
                details_json, actor, authority
            ) VALUES ('asset', ?, 'synthetic_conflict', 'conflict', '{}', ?, ?)
            """,
            (asset["asset_uuid"], self.actor.actor, self.actor.authority),
        )
        with self.assertRaises(ConflictError):
            self.registry.publish_asset(
                asset_uuid=asset["asset_uuid"], request_id="pub-conflict", actor=self.actor
            )

    def test_reservation_idempotency_rejects_changed_intent(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(
            asset_id, request_id="same", intended_asset_key="intent-a", actor=self.actor
        )
        with self.assertRaises(ConflictError):
            self.registry.reserve_asset_id(
                asset_id, request_id="same", intended_asset_key="intent-b", actor=self.actor
            )
        event = self.registry.conn.execute(
            """
            SELECT event_payload_json FROM audit_events
            WHERE event_type = 'failed_access'
            ORDER BY audit_event_id DESC LIMIT 1
            """
        ).fetchone()
        self.assertIn("intended_asset_key_changed", event["event_payload_json"])

    def test_assignment_idempotency_rejects_changed_intent(self):
        asset = self._assigned_asset(name="Assigned Idempotency")
        with self.assertRaises(ConflictError):
            self.registry.assign_asset(
                asset_id=asset["asset_id"],
                request_id=asset["assignment_request_id"],
                intended_asset_key="changed-intent",
                preferred_name="Hijack",
                description="Should not hijack",
                taxonomy_ref="tax:physical:tools",
                information_class="Personal",
                actor=self.actor,
            )

    def test_restricted_export_suppresses_protected_fields_and_hashes_payload(self):
        asset = self._assigned_asset(info_class="Restricted", name="Restricted Export")
        self.registry.add_external_identifier(
            asset_uuid=asset["asset_uuid"],
            identifier_type="synthetic-secret-like",
            normalized_value="RESTRICTED-EXT-001",
            display_value="Restricted external identifier",
            issuer_namespace="synthetic",
            information_class="Restricted",
            actor=self.actor,
        )
        self.registry.add_evidence_reference(
            asset_uuid=asset["asset_uuid"],
            evidence_ref="ev-restricted-export",
            evidence_type="restricted_reference",
            drive_locator="gdrive://synthetic/restricted/location",
            information_class="Restricted",
            original_or_derivative="original",
            continuity_state="available",
            acceptance_state="associated",
            completeness_state="partial",
            provenance={"synthetic": True},
            actor=self.actor,
        )
        out = Path(self.tmp.name) / "export.json"
        result = controlled_export(self.db_path, out, actor=self.actor)
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(result["integrity_hash"].startswith("sha256:"))
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotIn("Restricted controlled description", encoded)
        self.assertNotIn("gdrive://synthetic/restricted/location", encoded)
        self.assertIn("[suppressed]", encoded)

    def test_authorization_failures_and_controlled_operations_are_audited(self):
        limited = auth.ActorContext("limited", "synthetic", frozenset({auth.READ}))
        with self.assertRaises(AuthorizationError):
            self.registry.reserve_asset_id(
                self.registry.generate_candidate(),
                request_id="denied-reserve",
                intended_asset_key="denied-reserve",
                actor=limited,
            )
        with self.assertRaises(AuthorizationError):
            controlled_export(self.db_path, Path(self.tmp.name) / "denied.json", actor=limited)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            event_types = [row["event_type"] for row in conn.execute("SELECT event_type FROM audit_events")]
        finally:
            conn.close()
        self.assertGreaterEqual(event_types.count("failed_access"), 2)

    def test_export_backup_restore_audit_events_and_no_cli_passphrase(self):
        asset = self._assigned_asset(name="Audit Backup")
        self.registry.validate_asset(asset_uuid=asset["asset_uuid"], actor=self.actor)
        controlled_export(self.db_path, Path(self.tmp.name) / "export.json", actor=self.actor)
        backup_path = Path(self.tmp.name) / "backup.enc"
        restore_path = Path(self.tmp.name) / "restore.sqlite"
        passphrase = "synthetic-test-passphrase-not-logged"
        encrypted_backup(self.db_path, backup_path, passphrase=passphrase, actor=self.actor)
        restored_manifest = restore_encrypted_backup(
            backup_path, restore_path, passphrase=passphrase, actor=self.actor
        )
        self.assertEqual("AOS-HO-00001", restored_manifest["control_reference"])
        events = [
            row["event_type"] for row in self.registry.conn.execute("SELECT event_type FROM audit_events")
        ]
        self.assertIn("export", events)
        self.assertIn("backup", events)
        audit_json = " ".join(
            row["event_payload_json"] for row in self.registry.conn.execute("SELECT event_payload_json FROM audit_events")
        )
        self.assertNotIn(passphrase, audit_json)
        self.assertNotIn("pass:", backup_path.read_text(encoding="utf-8"))

    def test_search_supports_name_taxonomy_external_identifier_and_evidence_ref(self):
        asset = self._assigned_asset(name="Searchable Drill")
        self.registry.add_external_identifier(
            asset_uuid=asset["asset_uuid"],
            identifier_type="serial",
            normalized_value="SERIAL-SEARCH-001",
            display_value="Serial Search 001",
            issuer_namespace="synthetic",
            information_class="Personal",
            actor=self.actor,
        )
        self.registry.add_evidence_reference(
            asset_uuid=asset["asset_uuid"],
            evidence_ref="ev-searchable-drill",
            evidence_type="photo",
            drive_locator="gdrive://synthetic/searchable",
            information_class="Personal",
            original_or_derivative="original",
            continuity_state="available",
            acceptance_state="associated",
            completeness_state="partial",
            provenance={"synthetic": True},
            actor=self.actor,
        )
        for term in ("Searchable", "Tools", "SERIAL-SEARCH-001", "ev-searchable-drill"):
            with self.subTest(term=term):
                results = self.registry.limited_search(term, actor=self.actor)
                self.assertEqual(asset["asset_id"], results[0]["asset_id"])
                self.assertNotIn("description", results[0])

    def test_evidence_locator_repair_preserves_identity_and_history(self):
        asset = self._assigned_asset(name="Evidence Repair")
        evidence = self.registry.add_evidence_reference(
            asset_uuid=asset["asset_uuid"],
            evidence_ref="ev-repair",
            evidence_type="receipt",
            drive_locator="gdrive://synthetic/old",
            information_class="Confidential",
            original_or_derivative="original",
            continuity_state="broken",
            acceptance_state="associated",
            completeness_state="partial",
            provenance={"synthetic": True},
            actor=self.actor,
        )
        repaired = self.registry.repair_evidence_locator(
            evidence_ref=evidence["evidence_ref"],
            new_drive_locator="gdrive://synthetic/new",
            continuity_state="available",
            reason="synthetic locator repair",
            actor=self.actor,
        )
        self.assertEqual(evidence["evidence_ref"], repaired["evidence_ref"])
        history = self.registry.conn.execute(
            "SELECT * FROM evidence_locator_history WHERE evidence_ref = ?", ("ev-repair",)
        ).fetchone()
        self.assertEqual("gdrive://synthetic/old", history["prior_drive_locator"])
        self.assertEqual("gdrive://synthetic/new", history["new_drive_locator"])

    def test_original_derivative_states_are_explicit_and_historical(self):
        asset = self._assigned_asset(name="Derivative Evidence")
        with self.assertRaises(ValidationError):
            self.registry.add_evidence_reference(
                asset_uuid=asset["asset_uuid"],
                evidence_ref="ev-invalid-state",
                evidence_type="photo",
                drive_locator="gdrive://synthetic/invalid",
                information_class="Public",
                original_or_derivative="implicit",
                continuity_state="available",
                acceptance_state="associated",
                completeness_state="partial",
                provenance={"synthetic": True},
                actor=self.actor,
            )
        evidence = self.registry.add_evidence_reference(
            asset_uuid=asset["asset_uuid"],
            evidence_ref="ev-derivative",
            evidence_type="photo",
            drive_locator="gdrive://synthetic/derivative",
            information_class="Public",
            original_or_derivative="derivative",
            continuity_state="available",
            acceptance_state="associated",
            completeness_state="partial",
            provenance={"synthetic": True},
            actor=self.actor,
        )
        self.assertEqual("derivative", evidence["original_or_derivative"])
        changed = self.registry.set_evidence_state(
            evidence_ref="ev-derivative",
            original_or_derivative="redacted",
            reason="synthetic redaction",
            actor=self.actor,
        )
        self.assertEqual("redacted", changed["original_or_derivative"])
        count = self.registry.conn.execute(
            "SELECT COUNT(*) AS c FROM evidence_state_history WHERE evidence_ref = 'ev-derivative'"
        ).fetchone()["c"]
        self.assertEqual(2, count)


class AOSPROD001ProviderLocatorCorrections(_ProviderLocatorSemanticsTests):
    """AOS-PROD-001 provider identity and canonical locator adversarial coverage."""


class AOSPROD001SyntheticMigrationCorrections(_SyntheticV011MigrationTests):
    """Synthetic v0.1.1 to v0.1.2 migration adversarial coverage."""


del _ProviderLocatorSemanticsTests
del _SyntheticV011MigrationTests


if __name__ == "__main__":
    unittest.main()
