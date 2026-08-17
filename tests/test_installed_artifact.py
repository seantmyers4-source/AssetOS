import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import _bootstrap  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]


class InstalledArtifactTests(unittest.TestCase):
    def test_installed_package_initializes_without_repository_migrations(self):
        if not hasattr(sys, "base_prefix"):
            self.skipTest("virtual environment support unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            venv_path = tmp_path / "venv"
            run_path = tmp_path / "isolated-runtime"
            db_path = tmp_path / "installed.sqlite"
            run_path.mkdir()

            subprocess.run(
                [sys.executable, "-m", "venv", "--system-site-packages", str(venv_path)],
                check=True,
                cwd=tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            python = _venv_python(venv_path)
            subprocess.run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--no-index",
                    "--no-build-isolation",
                    str(ROOT),
                ],
                check=True,
                cwd=tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            script = """
import json
import sqlite3
from pathlib import Path
from assetos_mob.registry import AssetOSRegistry

db_path = Path(r"{db_path}")
registry = AssetOSRegistry(db_path)
registry.close()
conn = sqlite3.connect(db_path)
try:
    migrations = [row[0] for row in conn.execute(
        "SELECT version FROM schema_migrations ORDER BY version"
    )]
    information_classes = [row[0] for row in conn.execute(
        "SELECT information_class FROM information_classes ORDER BY information_class"
    )]
    taxonomy_count = conn.execute("SELECT COUNT(*) FROM taxonomy_terms").fetchone()[0]
finally:
    conn.close()
print(json.dumps({{
    "migrations": migrations,
    "information_classes": information_classes,
    "taxonomy_count": taxonomy_count,
}}))
""".format(db_path=db_path)

            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            result = subprocess.run(
                [str(python), "-c", script],
                check=True,
                cwd=run_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            observed = json.loads(result.stdout)
            self.assertEqual(["001_mob"], observed["migrations"])
            self.assertEqual(
                ["Confidential", "Personal", "Public", "Restricted"],
                observed["information_classes"],
            )
            self.assertGreaterEqual(observed["taxonomy_count"], 1)
            self.assertFalse((run_path / "migrations").exists())

    def test_packaged_migration_matches_governed_source_migration(self):
        source = ROOT / "migrations" / "001_mob.sql"
        packaged = ROOT / "src" / "assetos_mob" / "migrations" / "001_mob.sql"
        self.assertEqual(source.read_text(encoding="utf-8"), packaged.read_text(encoding="utf-8"))


def _venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


if __name__ == "__main__":
    unittest.main()
