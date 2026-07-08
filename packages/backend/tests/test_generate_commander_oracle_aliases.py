import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

try:
    import requests as requests_module  # noqa: F401
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_commander_oracle_aliases import build_arg_parser, write_output  # noqa: E402


class BuildArgParserTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_arg_parser().parse_args([])
        self.assertEqual(args.output, "packages/backend/data/commander_oracle_aliases.json")
        self.assertEqual(args.timeout, 120.0)

    def test_overrides(self) -> None:
        args = build_arg_parser().parse_args(["--output", "out.json", "--timeout", "5"])
        self.assertEqual(args.output, "out.json")
        self.assertEqual(args.timeout, 5.0)


class WriteOutputTests(unittest.TestCase):
    def test_writes_sorted_alias_payload(self) -> None:
        alias_map = {
            "Totally Radical Skater": "Nadier, Agent of the Duskenel",
            "Chief Jim Hopper": "Sophina, Spearsage Deserter",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "nested" / "aliases.json"
            write_output(alias_map, output_path=output_path, timeout=30.0)

            payload = json.loads(output_path.read_text())

        self.assertEqual(payload["alias_count"], 2)
        self.assertEqual(
            list(payload["aliases"].keys()),
            ["Chief Jim Hopper", "Totally Radical Skater"],
        )
        self.assertEqual(payload["source"]["dataset"], "default_cards")
        self.assertIn("generated_at", payload)


if __name__ == "__main__":
    unittest.main()
