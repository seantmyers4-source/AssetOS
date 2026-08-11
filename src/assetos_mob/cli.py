"""Small development CLI for the AssetOS MOB kernel."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import auth
from .export import controlled_export
from .fixtures import load_synthetic_fixtures
from .registry import AssetOSRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="AssetOS MOB development/test CLI")
    parser.add_argument("--db", required=True, help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("generate")
    load = sub.add_parser("load-fixtures")
    load.add_argument("fixture_path")
    exp = sub.add_parser("export")
    exp.add_argument("output_path")
    args = parser.parse_args()

    registry = AssetOSRegistry(Path(args.db))
    try:
        if args.command == "init":
            print(f"initialized {args.db}")
        elif args.command == "generate":
            print(registry.generate_candidate())
        elif args.command == "load-fixtures":
            print(load_synthetic_fixtures(registry, args.fixture_path))
        elif args.command == "export":
            print(controlled_export(args.db, args.output_path, actor=auth.ENGINEERING_TEST_ACTOR))
    finally:
        registry.close()
