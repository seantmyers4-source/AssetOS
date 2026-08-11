"""Synthetic fixture loading."""

from __future__ import annotations

from pathlib import Path
import json

from . import auth
from .registry import AssetOSRegistry


def load_synthetic_fixtures(registry: AssetOSRegistry, fixture_path: str | Path) -> list[dict]:
    data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    created: list[dict] = []
    for item in data["assets"]:
        candidate = registry.generate_candidate()
        registry.reserve_asset_id(
            candidate,
            request_id=item["request_id"],
            intended_asset_key=item["intended_asset_key"],
            actor=auth.ENGINEERING_TEST_ACTOR,
        )
        asset = registry.assign_asset(
            asset_id=candidate,
            request_id=item["request_id"],
            intended_asset_key=item["intended_asset_key"],
            preferred_name=item["preferred_name"],
            description=item["description"],
            taxonomy_ref=item["taxonomy_ref"],
            information_class=item["information_class"],
            actor=auth.ENGINEERING_TEST_ACTOR,
        )
        for evidence in item.get("evidence", []):
            registry.add_evidence_reference(
                asset_uuid=asset["asset_uuid"],
                actor=auth.ENGINEERING_TEST_ACTOR,
                **evidence,
            )
        created.append(asset)
    return created
