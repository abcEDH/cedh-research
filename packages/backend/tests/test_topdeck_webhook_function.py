import unittest
from pathlib import Path

FUNCTION_DIR = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "functions"
    / "topdeck-webhook"
)
INDEX_PATH = FUNCTION_DIR / "index.ts"
VERIFY_PATH = FUNCTION_DIR / "verify.ts"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "supabase" / "config.toml"


class TopdeckWebhookFunctionTests(unittest.TestCase):
    def test_function_files_exist(self) -> None:
        self.assertTrue(INDEX_PATH.exists(), f"Receiver not found at {INDEX_PATH}")
        self.assertTrue(VERIFY_PATH.exists(), f"Verifier not found at {VERIFY_PATH}")

    def test_signature_verified_over_raw_body_before_parse(self) -> None:
        source = INDEX_PATH.read_text()
        raw_body_index = source.index("await request.text()")
        verify_index = source.index("verifyTopdeckSignature(")
        parse_index = source.index("JSON.parse(rawBody)")
        self.assertLess(raw_body_index, verify_index)
        self.assertLess(verify_index, parse_index)

    def test_invalid_signature_returns_401_in_enforce_mode(self) -> None:
        source = INDEX_PATH.read_text()
        self.assertIn("json(401", source)
        self.assertIn('SIGNATURE_MODE !== "log"', source)

    def test_signature_comparison_is_constant_time(self) -> None:
        source = VERIFY_PATH.read_text()
        self.assertIn("timingSafeEqual", source)
        # A bare equality on the provided signature would leak timing.
        self.assertNotIn("candidate ===", source)
        self.assertNotIn("=== candidate", source)

    def test_duplicate_deliveries_are_ignored(self) -> None:
        source = INDEX_PATH.read_text()
        self.assertIn("resolution=ignore-duplicates", source)
        self.assertIn("duplicate: true", source)

    def test_receiver_does_not_dispatch_github_workflows(self) -> None:
        # Dispatch lives in the process_webhook_event DB trigger; the
        # internet-facing function must not hold a GitHub PAT.
        source = INDEX_PATH.read_text()
        self.assertNotIn("api.github.com", source)
        self.assertNotIn("GITHUB_PAT", source)

    def test_inbound_auth_headers_are_not_persisted(self) -> None:
        source = INDEX_PATH.read_text()
        self.assertIn('key === "authorization" || key === "apikey"', source)

    def test_config_disables_jwt_verification_for_receiver(self) -> None:
        config = CONFIG_PATH.read_text()
        self.assertIn("[functions.topdeck-webhook]", config)
        webhook_section = config.split("[functions.topdeck-webhook]", 1)[1]
        self.assertIn("verify_jwt = false", webhook_section.split("[", 1)[0])


if __name__ == "__main__":
    unittest.main()
