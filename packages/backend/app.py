"""Invite-only Vercel trial of the existing tournament simulation CLI.

Deploy this directory as a separate Python Vercel project. No public UI is enabled.
"""

import asyncio
import hmac
import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
BACKEND = Path(__file__).resolve().parent
WALL_SECONDS = 240
# This gate is per instance, not a distributed account-wide quota.
_busy = False


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    event_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,159}$")
    swiss_rounds: int = Field(ge=1, le=12)
    top_cut: int = Field(ge=0, le=64)
    run_seconds: int = Field(default=30, ge=1, le=120)
    simulations: int = Field(default=2000, ge=1, le=10000)
    seed: int = Field(default=1, ge=0, le=2147483647)
    drop_after_round: int | None = Field(default=None, ge=1)
    drop_min_points: int | None = Field(default=None, ge=0, le=60)

    @model_validator(mode="after")
    def validate_structure(self):
        if self.top_cut not in (0, 4, 10, 16, 40, 64):
            raise ValueError("Unsupported top cut")
        if (self.drop_after_round is None) != (self.drop_min_points is None):
            raise ValueError("Both drop settings are required together")
        if self.drop_after_round is not None and self.drop_after_round > self.swiss_rounds:
            raise ValueError("Drop round exceeds Swiss rounds")
        return self


def command(settings: SimulationRequest) -> list[str]:
    args = [
        sys.executable,
        "-u",
        str(BACKEND / "src/run_topdeck_ongoing_tournament_sim.py"),
        "--event-id",
        settings.event_id,
        "--swiss-rounds",
        str(settings.swiss_rounds),
        "--top-cut",
        str(settings.top_cut),
        "--simulations",
        str(settings.simulations),
        "--seed",
        str(settings.seed),
        "--workers",
        "1",
        "--stream",
        "--stream-batch-size",
        "1",
        "--stream-duration-seconds",
        str(settings.run_seconds),
        "--no-prepared-state-cache",
    ]
    if settings.drop_after_round is not None:
        args.extend(
            ["--drop-after-round", str(settings.drop_after_round), "--drop-min-points", str(settings.drop_min_points)]
        )
    return args


async def read_diagnostics(stream):
    """Drain stderr to avoid pipe deadlocks; retain only a bounded, redacted tail."""
    tail = b""
    while chunk := await stream.read(4096):
        tail = (tail + chunk)[-8192:]
    message = tail.decode("utf-8", errors="replace")
    for key in ("SIMULATOR_INVITE_TOKEN", "TOPDECK_API_KEY", "SUPABASE_SERVICE_KEY"):
        value = os.environ.get(key)
        if value:
            message = message.replace(value, "[redacted]")
    return message


async def snapshots(settings: SimulationRequest):
    global _busy
    process = None
    stderr_task = None
    try:
        # The existing CLI runs in an isolated Python process, with one worker.
        # Cancellation can stop CPU work without global stdout/argv mutations.
        async with asyncio.timeout(WALL_SECONDS):
            process = await asyncio.create_subprocess_exec(
                *command(settings),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path), "CEDH_LOG_DIR": "/tmp/cedh-simulator-logs"},
                cwd=BACKEND,
                limit=4 * 1024 * 1024,
            )
            stderr_task = asyncio.create_task(read_diagnostics(process.stderr))
            yield b'{"status":"starting"}\n'
            assert process.stdout is not None
            complete = False
            async for line in process.stdout:
                payload = json.loads(line)
                complete = payload.get("status") == "complete"
                yield json.dumps(payload, separators=(",", ":")).encode() + b"\n"
            code = await process.wait()
            if code != 0 or not complete:
                diagnostic = await stderr_task
                logging.error("Simulator worker exited %s: %s", code, diagnostic)
                yield b'{"status":"error","message":"Simulation did not complete."}\n'
    except TimeoutError:
        yield b'{"status":"error","message":"Simulation exceeded the time limit."}\n'
    except (OSError, ValueError):
        yield b'{"status":"error","message":"Simulation could not run."}\n'
    finally:
        try:
            if process is not None and process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                await process.wait()
        finally:
            _busy = False
            if stderr_task is not None:
                stderr_task.cancel()
                await asyncio.gather(stderr_task, return_exceptions=True)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/simulate")
async def simulate(settings: SimulationRequest, authorization: str | None = Header(default=None)):
    global _busy
    token = os.environ.get("SIMULATOR_INVITE_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(503, "Simulator is not configured")
    if not hmac.compare_digest((authorization or "").encode(), f"Bearer {token}".encode()):
        raise HTTPException(401, "Invite required")
    if not all(os.environ.get(key) for key in ("TOPDECK_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY")):
        raise HTTPException(503, "Simulator is not configured")
    if _busy:
        raise HTTPException(429, "Simulator is busy; retry later")
    _busy = True
    return StreamingResponse(
        snapshots(settings),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
