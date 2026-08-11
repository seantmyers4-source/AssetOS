import unittest

import _bootstrap  # noqa: F401

from assetos_mob.errors import ValidationError
from assetos_mob.identifiers import calculate_check_symbol, normalize_asset_id


class IdentifierTests(unittest.TestCase):
    def test_approved_deterministic_vectors(self):
        vectors = {
            "7K3M9Q2DX8RF4T6N": "AOS-7K3M-9Q2D-X8RF-4T6N-5",
            "0000000000000000": "AOS-0000-0000-0000-0000-0",
            "0000000000000001": "AOS-0000-0000-0000-0001-1",
            "ZZZZZZZZZZZZZZZZ": "AOS-ZZZZ-ZZZZ-ZZZZ-ZZZZ-~",
            "0123456789ABCDEF": "AOS-0123-4567-89AB-CDEF-K",
        }
        for body, canonical in vectors.items():
            with self.subTest(body=body):
                self.assertEqual(canonical[-1], calculate_check_symbol(body))
                self.assertEqual(canonical, normalize_asset_id(canonical).canonical)

    def test_invalid_check_symbol_fails_closed(self):
        with self.assertRaises(ValidationError):
            normalize_asset_id("AOS-7K3M-9Q2D-X8RF-4T6N-P")

    def test_invalid_body_symbol_is_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_asset_id("AOS-7K3M-9Q2D-X8RF-4T6U-5")

    def test_misplaced_grouping_is_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_asset_id("AOS-7K3M9-Q2D-X8RF-4T6N-5")


if __name__ == "__main__":
    unittest.main()
