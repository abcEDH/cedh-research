import { spawn } from "node:child_process";
import path from "node:path";
import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_SIMULATION_COUNT = 100000;
const MAX_TIMED_SIMULATION_COUNT = 1000000;
const STREAM_INTERVAL_SECONDS = 5;
const STREAM_BATCH_SIZE = 5;
const DEFAULT_RUN_SECONDS = 600;
const MAX_RUN_SECONDS = 10 * 60;

function readInteger(value: string | null, fallback: number, min: number) {
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= min ? parsed : fallback;
}

function readOptionalInteger(value: string | null, min: number) {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= min ? parsed : null;
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const slug = searchParams.get("tournament")?.trim();
  if (!slug) {
    return new Response("Missing tournament", { status: 400 });
  }

  const swissRounds = readInteger(searchParams.get("swissRounds"), 6, 1);
  const topCut = readInteger(searchParams.get("topCut"), 40, 0);
  const dropAfterRound = readOptionalInteger(searchParams.get("dropAfterRound"), 1);
  const dropMinPoints = readOptionalInteger(searchParams.get("dropMinPoints"), 0);
  const hasDropRule = dropAfterRound !== null && dropMinPoints !== null;
  const runSeconds = Math.min(
    readInteger(searchParams.get("runSeconds"), DEFAULT_RUN_SECONDS, 0),
    MAX_RUN_SECONDS
  );
  const simulationCount = runSeconds > 0 ? MAX_TIMED_SIMULATION_COUNT : DEFAULT_SIMULATION_COUNT;
  const repoRoot = path.join(/* turbopackIgnore: true */ process.cwd(), "../..");
  const pythonPath = path.join(repoRoot, "packages/backend/src");
  const scriptPath = path.join(pythonPath, "run_topdeck_ongoing_tournament_sim.py");
  const drawModelPath = path.join(
    repoRoot,
    "packages/backend/reports/pod-outcome-model/v4/pod_outcome_model_artifact_v4_draw_elo_hybrid.pkl"
  );

  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let closed = false;
      function enqueue(value: string) {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(value));
        } catch {
          closed = true;
        }
      }

      function close() {
        if (!closed) {
          closed = true;
          try {
            controller.close();
          } catch {
            // The client may have already closed the SSE connection.
          }
        }
      }

      const child = spawn(
        "python3",
        [
          scriptPath,
          "--event-id",
          slug,
          "--draw-model-path",
          drawModelPath,
          "--simulations",
          String(simulationCount),
          "--swiss-rounds",
          String(swissRounds),
          "--top-cut",
          String(topCut),
          ...(hasDropRule
            ? [
                "--drop-after-round",
                String(dropAfterRound),
                "--drop-min-points",
                String(dropMinPoints),
              ]
            : []),
          "--seed",
          "1",
          "--workers",
          "2",
          "--stream",
          "--stream-interval-seconds",
          String(STREAM_INTERVAL_SECONDS),
          "--stream-batch-size",
          String(STREAM_BATCH_SIZE),
          ...(runSeconds > 0 ? ["--stream-duration-seconds", String(runSeconds)] : []),
        ],
        {
          cwd: repoRoot,
          env: {
            ...process.env,
            PYTHONPATH: pythonPath,
          },
          stdio: ["ignore", "pipe", "pipe"],
        }
      );

      let stdoutBuffer = "";
      let stderrBuffer = "";

      child.stdout.on("data", (chunk: Buffer) => {
        stdoutBuffer += chunk.toString("utf8");
        const lines = stdoutBuffer.split("\n");
        stdoutBuffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          enqueue(`data: ${line}\n\n`);
        }
      });

      child.stderr.on("data", (chunk: Buffer) => {
        stderrBuffer += chunk.toString("utf8");
        if (stderrBuffer.length > 4000) {
          stderrBuffer = stderrBuffer.slice(-4000);
        }
      });

      child.on("error", (error) => {
        enqueue(`event: error\ndata: ${JSON.stringify({ message: error.message })}\n\n`);
        close();
      });

      child.on("close", (code) => {
        if (stdoutBuffer.trim()) {
          enqueue(`data: ${stdoutBuffer.trim()}\n\n`);
        }
        if (code !== 0) {
          enqueue(
            `event: error\ndata: ${JSON.stringify({
              message: "Simulation process failed.",
              detail: stderrBuffer.trim(),
            })}\n\n`
          );
        }
        close();
      });

      request.signal.addEventListener("abort", () => {
        closed = true;
        child.kill();
      });
    },
  });

  return new Response(stream, {
    headers: {
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Type": "text/event-stream",
    },
  });
}
