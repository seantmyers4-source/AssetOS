import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

try:
    import _bootstrap  # noqa: F401
except ModuleNotFoundError:
    import tests._bootstrap  # noqa: F401

from assetos_mob import auth
from assetos_mob.backup import encrypted_backup, restore_encrypted_backup
from assetos_mob.errors import AuthorizationError, ValidationError
from assetos_mob.export import controlled_export
from assetos_mob.identifiers import generate_candidate_asset_id
from assetos_mob.registry import AssetOSRegistry


PROVIDER_ID = "1aH_sXVfWyGq9Y7KXA-wj7GCBhR1jW9uR"
CANONICAL_LOCATOR = f"gdrive://file/{PROVIDER_ID}"


class ProviderLocatorSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "provider.sqlite"
        self.registry = AssetOSRegistry(self.db_path)
        self.actor = auth.ENGINEERING_TEST_ACTOR

    def tearDown(self):
        self.registry.close()
        self.tmp.cleanup()

    def _assigned_asset(self, *, name="Provider Evidence"):
        asset_id = self.registry.generate_candidate()
        request_id = name.lower().replace(" ", "-")
        self.registry.reserve_asset_id(
            asset_id,
            request_id=request_id,
            intended_asset_key=request_id,
            actor=self.actor,
        )
        return self.registry.assign_asset(
            asset_id=asset_id,
            request_id=request_id,
            intended_asset_key=request_id,
            preferred_name=name,
            description="Synthetic provider locator asset",
            taxonomy_ref="tax:physical:tools",
            information_class="Confidential",
            actor=self.actor,
        )

    def _provider_evidence(self):
        asset = self._assigned_asset()
        return self.registry.add_evidence_reference(
            asset_uuid=asset["asset_uuid"],
            evidence_ref="AOS-FIRST-PROD-EVIDENCE-001",
            evidence_type="photo",
            drive_locator="@Goal Zero Torch 250 - Original Identity Evidence.jpeg",
            information_class="Confidential",
            original_or_derivative="original",
            continuity_state="available",
            acceptance_state="associated",
            completeness_state="partial",
            provenance={"provider": "google_drive", "provider_object_id": PROVIDER_ID},
            provider_namespace="google_drive",
            provider_object_id=PROVIDER_ID,
            canonical_locator=CANONICAL_LOCATOR,
            display_name="Goal Zero Torch 250 - Original Identity Evidence.jpeg",
            actor=self.actor,
        )

    def test_provider_identity_and_canonical_locator_are_first_class(self):
        evidence = self._provider_evidence()
        self.assertEqual("google_drive", evidence["provider_namespace"])
        self.assertEqual(PROVIDER_ID, evidence["provider_object_id"])
        self.assertEqual(CANONICAL_LOCATOR, evidence["canonical_locator"])
        self.assertEqual("Goal Zero Torch 250 - Original Identity Evidence.jpeg", evidence["display_name"])

    def test_malformed_or_mismatched_provider_locator_is_rejected(self):
        asset = self._assigned_asset(name="Malformed Provider")
        with self.assertRaises(ValidationError):
            self.registry.add_evidence_reference(
                asset_uuid=asset["asset_uuid"],
                evidence_ref="ev-bad-locator",
                evidence_type="photo",
                drive_locator="https://drive.google.com/file/d/bad/view",
                information_class="Confidential",
                original_or_derivative="original",
                continuity_state="available",
                acceptance_state="associated",
                completeness_state="partial",
                provenance={"synthetic": True},
                provider_namespace="google_drive",
                provider_object_id=PROVIDER_ID,
                canonical_locator="gdrive://file/different-id",
                display_name="Bad locator",
                actor=self.actor,
            )

    def test_same_filename_wrong_object_is_rejected_before_locator_change(self):
        self._provider_evidence()
        wrong_provider_id = "1WRONGObjectIdWithSameHumanFilename"
        with self.assertRaises(ValidationError):
            self.registry.repair_evidence_locator(
                evidence_ref="AOS-FIRST-PROD-EVIDENCE-001",
                new_drive_locator=f"gdrive://file/{wrong_provider_id}",
                continuity_state="available",
                reason="same filename wrong provider object must not repair",
                provider_namespace="google_drive",
                provider_object_id=wrong_provider_id,
                actor=self.actor,
            )

    def test_no_op_repair_is_rejected_and_valid_repair_preserves_history(self):
        self._provider_evidence()
        with self.assertRaises(ValidationError):
            self.registry.repair_evidence_locator(
                evidence_ref="AOS-FIRST-PROD-EVIDENCE-001",
                new_drive_locator="@Goal Zero Torch 250 - Original Identity Evidence.jpeg",
                continuity_state="available",
                reason="same-value repair must not be history",
                provider_namespace="google_drive",
                provider_object_id=PROVIDER_ID,
                actor=self.actor,
            )
        repaired = self.registry.repair_evidence_locator(
            evidence_ref="AOS-FIRST-PROD-EVIDENCE-001",
            new_drive_locator=CANONICAL_LOCATOR,
            continuity_state="available",
            reason="canonical provider locator correction",
            provider_namespace="google_drive",
            provider_object_id=PROVIDER_ID,
            actor=self.actor,
        )
        self.assertEqual(CANONICAL_LOCATOR, repaired["drive_locator"])
        self.assertEqual(CANONICAL_LOCATOR, repaired["canonical_locator"])
        history = self.registry.conn.execute(
            "SELECT * FROM evidence_locator_history WHERE evidence_ref = 'AOS-FIRST-PROD-EVIDENCE-001'"
        ).fetchall()
        self.assertEqual(1, len(history))
        self.assertEqual("@Goal Zero Torch 250 - Original Identity Evidence.jpeg", history[0]["prior_drive_locator"])
        self.assertEqual(CANONICAL_LOCATOR, history[0]["new_drive_locator"])

    def test_historical_no_op_locator_events_can_be_annotated_without_rewrite(self):
        self._provider_evidence()
        for _ in range(2):
            self.registry.conn.execute(
                """
                INSERT INTO evidence_locator_history(
                    evidence_ref, prior_drive_locator, new_drive_locator,
                    continuity_state, actor, authority, reason
                ) VALUES (?, ?, ?, 'available', ?, ?, ?)
                """,
                (
                    "AOS-FIRST-PROD-EVIDENCE-001",
                    "@Goal Zero Torch 250 - Original Identity Evidence.jpeg",
                    "@Goal Zero Torch 250 - Original Identity Evidence.jpeg",
                    self.actor.actor,
                    self.actor.authority,
                    "synthetic historical no-op replica",
                ),
            )
        self.registry.conn.commit()
        before = [
            dict(row)
            for row in self.registry.conn.execute(
                "SELECT * FROM evidence_locator_history ORDER BY locator_history_id"
            )
        ]
        for row in before:
            self.registry.annotate_locator_history(
                locator_history_id=row["locator_history_id"],
                annotation_type="no_op_repair_attempt",
                annotation="not a canonical locator transition",
                actor=self.actor,
            )
        after = [
            dict(row)
            for row in self.registry.conn.execute(
                "SELECT * FROM evidence_locator_history ORDER BY locator_history_id"
            )
        ]
        self.assertEqual(before, after)
        annotation_count = self.registry.conn.execute(
            "SELECT COUNT(*) AS c FROM evidence_locator_annotations"
        ).fetchone()["c"]
        self.assertEqual(2, annotation_count)

    def test_provider_identity_survives_backup_restore(self):
        self._provider_evidence()
        backup_path = Path(self.tmp.name) / "provider.enc"
        restore_path = Path(self.tmp.name) / "provider-restored.sqlite"
        encrypted_backup(self.db_path, backup_path, passphrase="provider-test-passphrase", actor=self.actor)
        restore_encrypted_backup(backup_path, restore_path, passphrase="provider-test-passphrase", actor=self.actor)
        restored = AssetOSRegistry(restore_path)
        try:
            evidence = restored.conn.execute(
                "SELECT * FROM evidence_references WHERE evidence_ref = 'AOS-FIRST-PROD-EVIDENCE-001'"
            ).fetchone()
            self.assertEqual(PROVIDER_ID, evidence["provider_object_id"])
            self.assertEqual(CANONICAL_LOCATOR, evidence["canonical_locator"])
        finally:
            restored.close()

    def test_provider_locator_export_obeys_minimum_disclosure(self):
        self._provider_evidence()
        output = Path(self.tmp.name) / "export.json"
        controlled_export(self.db_path, output, actor=self.actor)
        encoded = output.read_text(encoding="utf-8")
        self.assertNotIn(PROVIDER_ID, encoded)
        self.assertNotIn(CANONICAL_LOCATOR, encoded)
        self.assertIn("[suppressed]", encoded)

    def test_provider_locator_authorization_enforced(self):
        evidence = self._provider_evidence()
        limited = auth.ActorContext("limited", "synthetic", frozenset({auth.READ}))
        with self.assertRaises(AuthorizationError):
            self.registry.set_evidence_provider_identity(
                evidence_ref=evidence["evidence_ref"],
                provider_namespace="google_drive",
                provider_object_id=PROVIDER_ID,
                canonical_locator=CANONICAL_LOCATOR,
                display_name="Goal Zero Torch 250 - Original Identity Evidence.jpeg",
                reason="denied provider identity update",
                actor=limited,
            )
        event = self.registry.conn.execute(
            """
            SELECT event_type FROM audit_events
            WHERE event_type = 'failed_access'
            ORDER BY audit_event_id DESC LIMIT 1
            """
        ).fetchone()
        self.assertIsNotNone(event)


class SyntheticV011MigrationTests(unittest.TestCase):
    def test_v011_synthetic_registry_migrates_and_preserves_identity_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "v011.sqlite"
            _create_synthetic_v011_database(db_path)
            registry = AssetOSRegistry(db_path)
            try:
                migrations = [
                    row["version"]
                    for row in registry.conn.execute("SELECT version FROM schema_migrations ORDER BY version")
                ]
                self.assertEqual(["001_mob", "002_provider_locator_semantics"], migrations)
                asset = registry.conn.execute(
                    "SELECT * FROM assets WHERE asset_id = 'AOS-P39J-030Z-B4RH-Q116-M'"
                ).fetchone()
                self.assertEqual("5e20035e-0a14-4bd4-bc6e-f085f9eff2b4", asset["asset_uuid"])
                evidence = registry.conn.execute(
                    "SELECT * FROM evidence_references WHERE evidence_ref = 'AOS-FIRST-PROD-EVIDENCE-001'"
                ).fetchone()
                self.assertEqual("@Goal Zero Torch 250 - Original Identity Evidence.jpeg", evidence["drive_locator"])
                self.assertIsNone(evidence["provider_namespace"])
                history_count = registry.conn.execute(
                    "SELECT COUNT(*) AS c FROM evidence_locator_history WHERE evidence_ref = ?",
                    ("AOS-FIRST-PROD-EVIDENCE-001",),
                ).fetchone()["c"]
                self.assertEqual(2, history_count)
                reconciled = registry.set_evidence_provider_identity(
                    evidence_ref="AOS-FIRST-PROD-EVIDENCE-001",
                    provider_namespace="google_drive",
                    provider_object_id=PROVIDER_ID,
                    canonical_locator=CANONICAL_LOCATOR,
                    display_name="Goal Zero Torch 250 - Original Identity Evidence.jpeg",
                    reason="synthetic provider identity reconciliation",
                    actor=auth.ENGINEERING_TEST_ACTOR,
                )
                self.assertEqual(PROVIDER_ID, reconciled["provider_object_id"])
            finally:
                registry.close()


def _create_synthetic_v011_database(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript((Path(__file__).resolve().parents[1] / "migrations" / "001_mob.sql").read_text())
        conn.execute(
            "CREATE TABLE schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.execute("INSERT INTO schema_migrations(version) VALUES ('001_mob')")
        for info_class in ("Public", "Personal", "Confidential", "Restricted"):
            conn.execute("INSERT OR IGNORE INTO information_classes(information_class) VALUES (?)", (info_class,))
        conn.execute(
            """
            INSERT OR IGNORE INTO taxonomy_terms(taxonomy_ref, root, class, category)
            VALUES ('tax:physical:tools', 'Asset', 'Physical', 'Tools')
            """
        )
        asset_id = "AOS-P39J-030Z-B4RH-Q116-M"
        asset_uuid = "5e20035e-0a14-4bd4-bc6e-f085f9eff2b4"
        parts = generate_candidate_asset_id()
        conn.execute(
            """
            INSERT INTO asset_id_reservations(
                asset_id, body, check_symbol, state, request_id, intended_asset_key,
                reserved_by, reserved_authority
            ) VALUES (?, ?, ?, 'reserved', 'first-prod', 'goal-zero-torch-250', 'synthetic', 'qa')
            """,
            (asset_id, parts.body, parts.check_symbol),
        )
        conn.execute(
            """
            INSERT INTO assets(
                asset_uuid, asset_id, assignment_request_id, intended_asset_key,
                preferred_name, description, record_state, validation_state,
                publication_state, created_by, created_authority
            ) VALUES (?, ?, 'first-prod', 'goal-zero-torch-250',
                'Goal Zero Torch 250', 'Synthetic v0.1.1 migration replica',
                'draft', 'pending', 'unpublished', 'synthetic', 'qa')
            """,
            (asset_uuid, asset_id),
        )
        conn.execute(
            """
            UPDATE asset_id_reservations
            SET state = 'assigned', assigned_asset_uuid = ?, assigned_at = CURRENT_TIMESTAMP
            WHERE asset_id = ?
            """,
            (asset_uuid, asset_id),
        )
        conn.execute(
            """
            INSERT INTO asset_assertions(
                assertion_id, asset_uuid, assertion_type, payload_json,
                actor, authority, reason, change_kind, dispute_state
            ) VALUES ('assertion-first-prod', ?, 'canonical_record', ?, 'synthetic', 'qa',
                'synthetic v0.1.1 replica', 'genuine_change', 'none')
            """,
            (
                asset_uuid,
                json.dumps(
                    {
                        "preferred_name": "Goal Zero Torch 250",
                        "description": "Synthetic v0.1.1 migration replica",
                        "taxonomy_ref": "tax:physical:tools",
                        "information_class": "Confidential",
                    },
                    sort_keys=True,
                ),
            ),
        )
        conn.execute(
            """
            INSERT INTO taxonomy_assignments(asset_uuid, taxonomy_ref, assignment_state, actor, authority, reason)
            VALUES (?, 'tax:physical:tools', 'proposed', 'synthetic', 'qa', 'synthetic')
            """,
            (asset_uuid,),
        )
        conn.execute(
            """
            INSERT INTO information_class_assignments(
                asset_uuid, information_class, assignment_state, actor, authority, reason
            ) VALUES (?, 'Confidential', 'proposed', 'synthetic', 'qa', 'synthetic')
            """,
            (asset_uuid,),
        )
        conn.execute(
            """
            INSERT INTO evidence_references(
                evidence_ref, asset_uuid, evidence_type, drive_locator, original_or_derivative,
                information_class, provenance_json, continuity_state, acceptance_state,
                completeness_state, actor, authority
            ) VALUES ('AOS-FIRST-PROD-EVIDENCE-001', ?, 'photo',
                '@Goal Zero Torch 250 - Original Identity Evidence.jpeg',
                'original', 'Confidential', ?, 'available', 'associated', 'partial', 'synthetic', 'qa')
            """,
            (
                asset_uuid,
                json.dumps(
                    {
                        "provider": "google_drive",
                        "provider_object_id": PROVIDER_ID,
                        "file_name": "Goal Zero Torch 250 - Original Identity Evidence.jpeg",
                    },
                    sort_keys=True,
                ),
            ),
        )
        for _ in range(2):
            conn.execute(
                """
                INSERT INTO evidence_locator_history(
                    evidence_ref, prior_drive_locator, new_drive_locator,
                    continuity_state, actor, authority, reason
                ) VALUES ('AOS-FIRST-PROD-EVIDENCE-001',
                    '@Goal Zero Torch 250 - Original Identity Evidence.jpeg',
                    '@Goal Zero Torch 250 - Original Identity Evidence.jpeg',
                    'available', 'synthetic', 'qa', 'synthetic no-op history')
                """
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    unittest.main()
