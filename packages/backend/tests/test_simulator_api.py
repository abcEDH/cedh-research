"""Security and lifecycle checks for the private Vercel proof of concept."""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient

import app as api

TOKEN = "test-invite-" + "x" * 32
ENV = {
    "SIMULATOR_INVITE_TOKEN": TOKEN,
    "TOPDECK_API_KEY": "test",
    "SUPABASE_URL": "test",
    "SUPABASE_SERVICE_KEY": "test",
}
BODY = {"event_id": "test-event", "swiss_rounds": 5, "top_cut": 16}


class SimulatorApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        api._busy = False

    def test_disabled_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.post("/simulate", json=BODY).status_code, 503)

    def test_uninvited_requests_never_start_worker(self):
        with patch.dict(os.environ, ENV), patch.object(api.asyncio, "create_subprocess_exec") as spawn:
            self.assertEqual(self.client.post("/simulate", json=BODY).status_code, 401)
            spawn.assert_not_called()

    def test_bounds_and_drop_pair(self):
        for overrides in (
            {"event_id": "../secret"},
            {"run_seconds": 121},
            {"swiss_rounds": 1.5},
            {"top_cut": 5},
            {"drop_after_round": 2},
            {"simulations": 10001},
        ):
            with self.subTest(overrides=overrides), patch.dict(os.environ, ENV):
                response = self.client.post(
                    "/simulate", json=BODY | overrides, headers={"Authorization": f"Bearer {TOKEN}"}
                )
                self.assertEqual(response.status_code, 422)

    def test_busy(self):
        api._busy = True
        with patch.dict(os.environ, ENV):
            response = self.client.post("/simulate", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(response.status_code, 429)

    def test_streams_real_child_output_and_releases_gate(self):
        child = [sys.executable, "-u", "-c", 'print(\'{"status":"complete","simulations":1}\')']
        with patch.dict(os.environ, ENV), patch.object(api, "command", return_value=child):
            response = self.client.post("/simulate", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.text.splitlines()[-1])["status"], "complete")
        self.assertFalse(api._busy)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_timeout_kills_worker(self):
        child = [sys.executable, "-c", "import time; time.sleep(30)"]
        with (
            patch.dict(os.environ, ENV),
            patch.object(api, "command", return_value=child),
            patch.object(api, "WALL_SECONDS", 0.1),
        ):
            response = self.client.post("/simulate", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(json.loads(response.text.splitlines()[-1])["status"], "error")
        self.assertFalse(api._busy)

    def test_disconnect_kills_worker(self):
        async def check():
            child = [sys.executable, "-c", "import time; time.sleep(30)"]
            with patch.object(api, "command", return_value=child):
                stream = api.snapshots(api.SimulationRequest(**BODY))
                await anext(stream)
                await stream.aclose()
            self.assertFalse(api._busy)

        asyncio.run(check())

    def test_worker_inherits_runtime_dependency_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "vercel_trial_dependency.py").write_text("VALUE = 42")
            child = [
                sys.executable,
                "-c",
                'import vercel_trial_dependency, json; print(json.dumps(dict(status="complete")))',
            ]
            with (
                patch.object(sys, "path", [directory, *sys.path]),
                patch.dict(os.environ, ENV),
                patch.object(api, "command", return_value=child),
            ):
                response = self.client.post("/simulate", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"})
            self.assertEqual(json.loads(response.text.splitlines()[-1])["status"], "complete")

    def test_zero_cut_and_single_worker_command(self):
        args = api.command(api.SimulationRequest(**(BODY | {"top_cut": 0})))
        self.assertEqual(args[args.index("--top-cut") + 1], "0")
        self.assertEqual(args[args.index("--workers") + 1], "1")
        self.assertNotIn("--sample-top-cut", args)
        from ongoing_tournament_inputs import infer_structure

        self.assertEqual(infer_structure({"topCut": 16}, "", swiss_rounds_override=5, top_cut_override=0), (5, 0))
