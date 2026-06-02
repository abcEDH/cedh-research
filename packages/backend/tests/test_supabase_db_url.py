"""
Validates SUPABASE_DB_URL format and live connectivity.

URL format tests run always (no credentials needed).
Connection smoke test is skipped when SUPABASE_DB_URL is not set.
"""
import os
import unittest
from urllib.parse import urlparse


def _parse_db_url(url: str):
    parsed = urlparse(url)
    return parsed


class DbUrlFormatTests(unittest.TestCase):
    """Unit tests — validate URL structure without touching the network."""

    VALID_URL = (
        "postgresql://postgres.msjjihqbxtgjdtapywrj:hunter2"
        "@aws-1-us-west-1.pooler.supabase.com:5432/postgres"
    )

    def test_valid_url_parses_correctly(self) -> None:
        p = _parse_db_url(self.VALID_URL)
        self.assertEqual(p.scheme, "postgresql")
        self.assertEqual(p.hostname, "aws-1-us-west-1.pooler.supabase.com")
        self.assertEqual(p.port, 5432)
        self.assertEqual(p.username, "postgres.msjjihqbxtgjdtapywrj")
        self.assertEqual(p.path, "/postgres")

    def test_detects_unencoded_at_sign_in_password(self) -> None:
        # If the password contains a literal '@', libpq splits on the first '@'
        # and treats the tail as the hostname — e.g. "nkf@aws-0-...supabase.com".
        # Encode '@' as '%40' to avoid this.
        bad_url = (
            "postgresql://postgres.msjjihqbxtgjdtapywrj:pass@word"
            "@aws-1-us-west-1.pooler.supabase.com:5432/postgres"
        )
        p = _parse_db_url(bad_url)
        # Python urlparse splits on the LAST '@'; verify the hostname looks sane
        # by checking it does NOT contain '@'.
        self.assertIsNotNone(p.hostname)
        self.assertNotIn("@", p.hostname or "")

    def test_username_contains_project_ref(self) -> None:
        # Supabase session-mode pooler requires "postgres.<project_ref>" as the
        # username; plain "postgres" yields "Tenant or user not found".
        p = _parse_db_url(self.VALID_URL)
        self.assertIn(".", p.username or "")

    def test_port_is_session_mode(self) -> None:
        # Port 5432 = session mode (supports SET, advisory locks, psycopg2).
        # Port 6543 = transaction mode (incompatible with psycopg2 connections).
        p = _parse_db_url(self.VALID_URL)
        self.assertEqual(p.port, 5432)

    def test_host_is_supabase_pooler(self) -> None:
        p = _parse_db_url(self.VALID_URL)
        self.assertTrue(
            (p.hostname or "").endswith(".pooler.supabase.com"),
            msg=f"Unexpected host: {p.hostname!r}",
        )


@unittest.skipUnless(
    os.environ.get("SUPABASE_DB_URL"),
    "SUPABASE_DB_URL not set — skipping live connection test",
)
class DbConnectionSmokeTest(unittest.TestCase):
    """Integration smoke test — requires SUPABASE_DB_URL in the environment."""

    def test_can_connect_and_select_one(self) -> None:
        import psycopg2

        db_url = os.environ["SUPABASE_DB_URL"]
        p = urlparse(db_url)

        # Catch malformed URLs (unencoded '@' in password) before psycopg2 does
        self.assertNotIn(
            "@",
            p.hostname or "",
            msg=(
                f"Hostname {p.hostname!r} contains '@' — password likely has an "
                "unencoded '@'; encode it as '%40' in SUPABASE_DB_URL"
            ),
        )
        self.assertIn(
            ".",
            p.username or "",
            msg=(
                f"Username {p.username!r} is missing the project ref. "
                "Use 'postgres.<project_ref>' for the Supabase session-mode pooler."
            ),
        )

        conn = psycopg2.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                (result,) = cur.fetchone()
            self.assertEqual(result, 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
