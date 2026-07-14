import json
import os
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

from generate_commander_oracle_aliases import (  # noqa: E402
    build_arg_parser,
    default_output_path,
    resolve_output_path,
    write_output,
)

EXPECTED_DEFAULT_OUTPUT_SUFFIX = Path("packages") / "backend" / "data" / "commander_oracle_aliases.json"


class BuildArgParserTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_arg_parser().parse_args([])
        self.assertIsNone(args.output)
        self.assertEqual(args.timeout, 120.0)

    def test_overrides(self) -> None:
        args = build_arg_parser().parse_args(["--output", "out.json", "--timeout", "5"])
        self.assertEqual(args.output, Path("out.json"))
        self.assertEqual(args.timeout, 5.0)


class DefaultOutputPathTests(unittest.TestCase):
    """Regression tests for the cwd-independence bug: the generator's default
    output path must resolve relative to the script's own location, not the
    caller's current working directory, or `--output`'s default silently
    writes to `packages/backend/packages/backend/data/...` when run with
    `packages/backend` as cwd (see PR #265 review discussion)."""

    def test_default_output_path_is_correct_absolute_path(self) -> None:
        path = default_output_path()
        self.assertTrue(path.is_absolute())
        self.assertEqual(path.parts[-4:], EXPECTED_DEFAULT_OUTPUT_SUFFIX.parts)

    def test_default_output_path_independent_of_cwd(self) -> None:
        expected = default_output_path()
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                self.assertEqual(default_output_path(), expected)
            finally:
                os.chdir(original_cwd)

    def test_resolve_output_path_falls_back_to_default(self) -> None:
        self.assertEqual(resolve_output_path(None), default_output_path())

    def test_resolve_output_path_honors_explicit_override(self) -> None:
        override = Path("some/other/aliases.json")
        self.assertEqual(resolve_output_path(override), override)


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
        self.assertEqual(payload["source"]["dataset"], "commander_eligible_prints")
        self.assertIn("generated_at", payload)


if __name__ == "__main__":
    unittest.main()
