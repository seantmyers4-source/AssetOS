import tempfile
from pathlib import Path
import unittest

import _bootstrap  # noqa: F401

from assetos_mob import auth
from assetos_mob.errors import ConflictError, ValidationError
from assetos_mob.identifiers import normalize_asset_id
from assetos_mob.registry import AssetOSRegistry


class ARIR013AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = AssetOSRegistry(Path(self.tmp.name) / "acceptance.sqlite")
        self.actor = auth.ENGINEERING_TEST_ACTOR

    def tearDown(self):
        self.registry.close()
        self.tmp.cleanup()

    def test_identity_invalid_check_cannot_reserve(self):
        with self.assertRaises(ValidationError):
            self.registry.reserve_asset_id(
                "AOS-0000-0000-0000-0001-0",
                request_id="bad-check",
                intended_asset_key="bad-check",
                actor=self.actor,
            )

    def test_valid_but_unissued_is_distinct_from_invalid(self):
        asset_id = self.registry.generate_candidate()
        normalize_asset_id(asset_id)
        with self.assertRaises(Exception) as cm:
            self.registry.lookup_asset_id(asset_id, actor=self.actor)
        self.assertIn("not found", str(cm.exception))

    def test_taxonomy_optional_precision_does_not_require_unknown_term(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(asset_id, request_id="taxonomy", intended_asset_key="taxonomy", actor=self.actor)
        asset = self.registry.assign_asset(
            asset_id=asset_id,
            request_id="taxonomy",
            intended_asset_key="taxonomy",
            preferred_name="Optional precision asset",
            description="Uses class and category only",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        row = self.registry.conn.execute(
            """
            SELECT tt.subcategory, tt.type
            FROM taxonomy_assignments ta
            JOIN taxonomy_terms tt ON tt.taxonomy_ref = ta.taxonomy_ref
            WHERE ta.asset_uuid = ?
            """,
            (asset["asset_uuid"],),
        ).fetchone()
        self.assertIsNone(row["subcategory"])
        self.assertIsNone(row["type"])

    def test_information_class_is_independent_from_taxonomy(self):
        first = self.registry.generate_candidate()
        second = self.registry.generate_candidate()
        self.registry.reserve_asset_id(first, request_id="ic1", intended_asset_key="same-tax-1", actor=self.actor)
        self.registry.reserve_asset_id(second, request_id="ic2", intended_asset_key="same-tax-2", actor=self.actor)
        a = self.registry.assign_asset(
            asset_id=first,
            request_id="ic1",
            intended_asset_key="same-tax-1",
            preferred_name="Public tool",
            description="Same taxonomy public",
            taxonomy_ref="tax:physical:tools",
            information_class="Public",
            actor=self.actor,
        )
        b = self.registry.assign_asset(
            asset_id=second,
            request_id="ic2",
            intended_asset_key="same-tax-2",
            preferred_name="Restricted tool",
            description="Same taxonomy restricted",
            taxonomy_ref="tax:physical:tools",
            information_class="Restricted",
            actor=self.actor,
        )
        classes = {
            row["asset_uuid"]: row["information_class"]
            for row in self.registry.conn.execute("SELECT asset_uuid, information_class FROM information_class_assignments")
        }
        self.assertEqual("Public", classes[a["asset_uuid"]])
        self.assertEqual("Restricted", classes[b["asset_uuid"]])

    def test_duplicate_request_cannot_manufacture_second_asset(self):
        asset_id = self.registry.generate_candidate()
        self.registry.reserve_asset_id(asset_id, request_id="dup", intended_asset_key="dup", actor=self.actor)
        self.registry.assign_asset(
            asset_id=asset_id,
            request_id="dup",
            intended_asset_key="dup",
            preferred_name="Duplicate protected",
            description="Original",
            taxonomy_ref="tax:physical:tools",
            information_class="Personal",
            actor=self.actor,
        )
        other = self.registry.generate_candidate()
        with self.assertRaises(ConflictError):
            self.registry.assign_asset(
                asset_id=other,
                request_id="dup",
                intended_asset_key="dup",
                preferred_name="Duplicate protected",
                description="Retry with different id",
                taxonomy_ref="tax:physical:tools",
                information_class="Personal",
                actor=self.actor,
            )


if __name__ == "__main__":
    unittest.main()
