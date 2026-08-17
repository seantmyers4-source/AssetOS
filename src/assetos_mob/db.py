"""SQLite connection and migration helpers."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import sqlite3

MIGRATIONS_PACKAGE = "assetos_mob.migrations"


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute("PRAGMA trusted_schema = OFF")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    for migration in sorted(_migration_resources(), key=lambda resource: resource.name):
        version = migration.name.removesuffix(".sql")
        exists = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone()
        if exists:
            continue
        with conn:
            conn.executescript(migration.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))


def _migration_resources() -> list[resources.abc.Traversable]:
    migrations = resources.files(MIGRATIONS_PACKAGE)
    return [
        resource
        for resource in migrations.iterdir()
        if resource.is_file() and resource.name.endswith(".sql")
    ]
