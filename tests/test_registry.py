import tempfile
from pathlib import Path
import unittest

import _bootstrap  # noqa: F401

from assetos_mob import auth
from assetos_mob.backup import encrypted_backup, restore_encrypted_backup
from assetos_mob.errors import AuthorizationError, ConflictError, NotFoundError, UncertainCommitError
from assetos_mob.export import controlled_export
from assetos_mob.fixtures import load_synthetic_fixtures
from assetos_mob.registry import AssetOSRegistry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "assetos.sqlite"
        self.registry = AssetOSRegistry(self.db_path)
        self.actor = auth.ENGINEERING_TEST_ACTOR

    def tearDown(self):
        self.registry.close()
        self.tmp.cleanup()

    def test_generate_validate_reserve_assign_workflow(self):
        asset_id = self.registry.generate_candidate()
        reservation = self.registry.reserve_asset_id(
            asset_id,
            request_id="req-1",
            intended_asset_key="asset-key-1",
            actor=self.actor,
        )
        self.assertEqual("reserved", reservation["state"])
        asset = self.registry.assign_asset(
            asset_id=asset_id,
            request_id="req-1",
            intended_asset_key="asset-key-1",
            preferred_name="Synthetic asset",
            description="Synthetic asset for workflow test",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        self.assertEqual(asset_id, asset["asset_id"])
        current = self.registry.lookup_asset_id(asset_id, actor=self.actor)
        self.assertEqual("Synthetic asset", current["preferred_name"])

    def test_reservation_and_assignment_are_idempotent_by_request(self):
        asset_id = self.registry.generate_candidate()
        first = self.registry.reserve_asset_id(
            asset_id,
            request_id="same-request",
            intended_asset_key="stable-intent",
            actor=self.actor,
        )
        second = self.registry.reserve_asset_id(
            asset_id,
            request_id="same-request",
            intended_asset_key="stable-intent",
            actor=self.actor,
        )
        self.assertEqual(first["asset_id"], second["asset_id"])
        assigned1 = self.registry.assign_asset(
            asset_id=asset_id,
            request_id="same-request",
            intended_asset_key="stable-intent",
            preferred_name="Synthetic idempotent asset",
            description="First assignment",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        assigned2 = self.registry.assign_asset(
            asset_id=asset_id,
            request_id="same-request",
            intended_asset_key="stable-intent",
            preferred_name="Synthetic idempotent asset",
            description="Retry assignment",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        self.assertEqual(assigned1["asset_uuid"], assigned2["asset_uuid"])

    def test_duplicate_active_reservation_is_rejected(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(
            asset_id,
            request_id="req-a",
            intended_asset_key="intent-a",
            actor=self.actor,
        )
        with self.assertRaises(ConflictError):
            self.registry.reserve_asset_id(
                asset_id,
                request_id="req-b",
                intended_asset_key="intent-b",
                actor=self.actor,
            )

    def test_assignment_without_reservation_is_rejected(self):
        with self.assertRaises(ConflictError):
            self.registry.assign_asset(
                asset_id=self.registry.generate_candidate(),
                request_id="missing-reservation",
                intended_asset_key="intent",
                preferred_name="No reservation",
                description="Should fail",
                taxonomy_ref="tax:physical:tools",
                information_class="Personal",
                actor=self.actor,
            )

    def test_uncertain_commit_requires_reconciliation(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(
            asset_id,
            request_id="uncertain",
            intended_asset_key="intent-uncertain",
            actor=self.actor,
        )
        with self.assertRaises(UncertainCommitError):
            self.registry.assign_asset(
                asset_id=asset_id,
                request_id="uncertain",
                intended_asset_key="intent-uncertain",
                preferred_name="Uncertain",
                description="Simulated uncertain commit",
                taxonomy_ref="tax:physical:tools",
                information_class="Personal",
                actor=self.actor,
                simulate_uncertain_commit=True,
            )
        with self.assertRaises(NotFoundError):
            self.registry.lookup_asset_id(asset_id, actor=self.actor)

    def test_append_supersede_preserves_history_and_current_view(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(asset_id, request_id="hist", intended_asset_key="hist", actor=self.actor)
        asset = self.registry.assign_asset(
            asset_id=asset_id,
            request_id="hist",
            intended_asset_key="hist",
            preferred_name="Original name",
            description="Original",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        self.registry.supersede_canonical_assertion(
            asset_uuid=asset["asset_uuid"],
            payload={
                "preferred_name": "Corrected name",
                "description": "Corrected",
                "taxonomy_ref": "tax:physical:tools",
                "information_class": "Personal",
            },
            reason="synthetic correction",
            change_kind="correction",
            actor=self.actor,
        )
        rows = self.registry.conn.execute(
            "SELECT COUNT(*) AS c FROM asset_assertions WHERE asset_uuid = ?",
            (asset["asset_uuid"],),
        ).fetchone()
        self.assertEqual(2, rows["c"])

    def test_authorization_denial(self):
        limited = auth.ActorContext("reader", "test", frozenset({auth.READ}))
        with self.assertRaises(AuthorizationError):
            self.registry.reserve_asset_id(
                self.registry.generate_candidate(),
                request_id="denied",
                intended_asset_key="denied",
                actor=limited,
            )

    def test_evidence_broken_locator_preserves_relationship(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(asset_id, request_id="ev", intended_asset_key="ev", actor=self.actor)
        asset = self.registry.assign_asset(
            asset_id=asset_id,
            request_id="ev",
            intended_asset_key="ev",
            preferred_name="Evidence asset",
            description="Evidence test",
            taxonomy_ref="tax:physical:tools",
            information_class="Confidential",
            actor=self.actor,
        )
        evidence = self.registry.add_evidence_reference(
            asset_uuid=asset["asset_uuid"],
            evidence_ref="ev-broken",
            evidence_type="receipt",
            drive_locator="gdrive://synthetic/missing",
            information_class="Confidential",
            original_or_derivative="original",
            continuity_state="broken",
            acceptance_state="associated",
            completeness_state="partial",
            provenance={"synthetic": True},
            actor=self.actor,
        )
        self.assertEqual("broken", evidence["continuity_state"])

    def test_synthetic_fixtures_load(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_assets.json"
        created = load_synthetic_fixtures(self.registry, fixture)
        self.assertEqual(4, len(created))

    def test_controlled_export_has_hash(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(asset_id, request_id="export", intended_asset_key="export", actor=self.actor)
        self.registry.assign_asset(
            asset_id=asset_id,
            request_id="export",
            intended_asset_key="export",
            preferred_name="Exportable asset",
            description="Export test",
            taxonomy_ref="tax:physical:tools",
            information_class="Public",
            actor=self.actor,
        )
        result = controlled_export(self.db_path, Path(self.tmp.name) / "export.json", actor=self.actor)
        self.assertTrue(result["integrity_hash"].startswith("sha256:"))

    def test_backup_restore_round_trip(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(asset_id, request_id="backup", intended_asset_key="backup", actor=self.actor)
        self.registry.assign_asset(
            asset_id=asset_id,
            request_id="backup",
            intended_asset_key="backup",
            preferred_name="Backup asset",
            description="Backup test",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        backup_path = Path(self.tmp.name) / "backup.enc"
        restore_path = Path(self.tmp.name) / "restore.sqlite"
        encrypted_backup(self.db_path, backup_path, passphrase="synthetic-test-passphrase", actor=self.actor)
        restore_encrypted_backup(backup_path, restore_path, passphrase="synthetic-test-passphrase", actor=self.actor)
        restored = AssetOSRegistry(restore_path)
        try:
            self.assertEqual("Backup asset", restored.lookup_asset_id(asset_id, actor=self.actor)["preferred_name"])
        finally:
            restored.close()


if __name__ == "__main__":
    unittest.main()
