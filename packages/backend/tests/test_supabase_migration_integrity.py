import unittest
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"


class SupabaseMigrationIntegrityTests(unittest.TestCase):
    def test_migration_versions_are_unique(self) -> None:
        versions = []
        for path in MIGRATIONS_DIR.glob("*.sql"):
            versions.append(path.name.split("_", 1)[0])

        duplicates = sorted(
            {version for version in versions if versions.count(version) > 1}
        )

        self.assertEqual(duplicates, [], f"duplicate migration versions found: {duplicates}")


if __name__ == "__main__":
    unittest.main()
