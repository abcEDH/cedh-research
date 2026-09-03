"""Prefect orchestration for the production backend refresh pipeline."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.logging import get_run_logger
from prefect.runtime import flow_run

from supabase_client import SupabaseClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = Path(__file__).resolve().parent


def runtime_secret(environment_name: str, block_name: str, *, required: bool = True) -> str | None:
    """Read an environment secret, falling back to a Prefect Secret block."""
    value = os.environ.get(environment_name)
    if value:
        return value
    try:
        return Secret.load(block_name).get()
    except ValueError:
        if required:
            raise
        return None


def runtime_environment() -> dict[str, str]:
    """Build the CLI environment from deployment variables or Prefect blocks."""
    environment = os.environ.copy()
    for environment_name, block_name in (
        ("SUPABASE_URL", "cedh-supabase-url"),
        ("SUPABASE_SERVICE_KEY", "cedh-supabase-service-key"),
        ("TOPDECK_API_KEY", "cedh-topdeck-api-key"),
    ):
        environment[environment_name] = runtime_secret(environment_name, block_name) or ""
    db_url = runtime_secret("SUPABASE_DB_URL", "cedh-supabase-db-url", required=False)
    if db_url:
        environment["SUPABASE_DB_URL"] = db_url
    return environment


@task(name="enqueue-job", retries=2, retry_delay_seconds=30)
def enqueue_job(function_name: str, idempotency_key: str) -> str | None:
    """Create one durable Supabase job, returning None when one is active."""
    url = runtime_secret("SUPABASE_URL", "cedh-supabase-url")
    key = runtime_secret("SUPABASE_SERVICE_KEY", "cedh-supabase-service-key")
    client = SupabaseClient(url, key)
    job_id = client.rpc(
        function_name,
        {"p_trigger_source": "prefect", "p_idempotency_key": idempotency_key},
    )
    return str(job_id) if job_id else None


@task(name="link-elo-job")
def link_elo_job(ingestion_job_id: str, elo_job_id: str) -> None:
    """Record the downstream Elo job on the completed ingestion ledger row."""
    url = runtime_secret("SUPABASE_URL", "cedh-supabase-url")
    key = runtime_secret("SUPABASE_SERVICE_KEY", "cedh-supabase-service-key")
    client = SupabaseClient(url, key)
    client.update(
        "ingestion_jobs",
        {"chained_elo_job_id": elo_job_id},
        {"id": f"eq.{ingestion_job_id}"},
    )


@task(name="run-backend-command", retries=0)
def run_backend_command(arguments: Sequence[str], continue_on_error: bool = False) -> bool:
    """Run an existing backend CLI as a visible Prefect task."""
    logger = get_run_logger()
    command = [sys.executable, *arguments]
    logger.info("Running: %s", " ".join(command))
    try:
        subprocess.run(command, cwd=BACKEND_ROOT, check=True, env=runtime_environment())
    except subprocess.CalledProcessError:
        if not continue_on_error:
            raise
        logger.warning("Command failed; continuing refresh: %s", " ".join(command))
        return False
    return True


@flow(name="daily-backend-refresh", log_prints=True)
def daily_backend_refresh(days: int = 7, min_players: int = 16) -> str:
    """Ingest recent tournaments, rebuild Elo, then publish derived profiles."""
    logger = get_run_logger()
    run_key = str(flow_run.id)
    ingestion_job_id = enqueue_job("enqueue_ingestion_refresh", f"{run_key}:ingestion")
    if not ingestion_job_id:
        logger.info("An ingestion job is already active; skipping this run.")
        return "skipped: ingestion already active"

    run_backend_command(
        [
            str(SRC_ROOT / "ingest.py"),
            "--days",
            str(days),
            "--min-players",
            str(min_players),
            "--job-id",
            ingestion_job_id,
        ]
    )
    run_backend_command(
        [str(SRC_ROOT / "sweep_partner_commander_order.py")],
        continue_on_error=True,
    )

    elo_job_id = enqueue_job("enqueue_elo_refresh", f"{run_key}:elo")
    if not elo_job_id:
        raise RuntimeError("Ingestion completed but Elo enqueue was rejected")
    link_elo_job(ingestion_job_id, elo_job_id)

    run_backend_command(
        [str(SRC_ROOT / "regional_elo.py"), "--apply", "--job-id", elo_job_id]
    )
    run_backend_command([str(SRC_ROOT / "rebuild_player_commander_profiles.py")])
    logger.info("Backend refresh completed: ingestion=%s elo=%s", ingestion_job_id, elo_job_id)
    return "completed"


if __name__ == "__main__":
    daily_backend_refresh()
