const SUPABASE_URL = Deno.env.get("SUPABASE_URL");
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY");
const GITHUB_PAT = Deno.env.get("GITHUB_PAT");
const GITHUB_OWNER = Deno.env.get("GITHUB_OWNER") ?? "abcEDH";
const GITHUB_REPO = Deno.env.get("GITHUB_REPO") ?? "cedh-research";
const GITHUB_WORKFLOW_ID = Deno.env.get("GITHUB_WORKFLOW_ID") ??
  "ci-backend-ingestion.yml";
const GITHUB_REF = Deno.env.get("GITHUB_REF") ?? "main";

type JobRow = {
  id: string;
  status: string;
};

function json(status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requireEnv(name: string, value: string | undefined): string {
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

async function supabaseRequest<T>(path: string, init: RequestInit): Promise<T> {
  const baseUrl = requireEnv("SUPABASE_URL", SUPABASE_URL);
  const serviceRoleKey = requireEnv(
    "SUPABASE_SERVICE_ROLE_KEY",
    SUPABASE_SERVICE_ROLE_KEY,
  );
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      Prefer: "return=representation",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(
      `Supabase request failed: ${response.status} ${await response.text()}`,
    );
  }

  if (response.status === 204) return null as T;
  return (await response.json()) as T;
}

async function getPendingJob(jobId: string): Promise<JobRow | null> {
  const rows = await supabaseRequest<JobRow[]>(
    `/rest/v1/ingestion_jobs?id=eq.${
      encodeURIComponent(jobId)
    }&status=eq.pending&select=id,status`,
    { method: "GET" },
  );
  return rows[0] ?? null;
}

async function markDispatched(jobId: string): Promise<void> {
  await supabaseRequest<JobRow[]>(
    `/rest/v1/ingestion_jobs?id=eq.${
      encodeURIComponent(jobId)
    }&status=eq.pending`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status: "dispatched",
        dispatched_at: new Date().toISOString(),
      }),
    },
  );
}

async function markFailed(jobId: string, errorText: string): Promise<void> {
  await supabaseRequest<JobRow[]>(
    `/rest/v1/ingestion_jobs?id=eq.${
      encodeURIComponent(jobId)
    }&status=in.(pending,dispatched)`,
    {
      method: "PATCH",
      body: JSON.stringify({
        status: "failed",
        completed_at: new Date().toISOString(),
        error_text: errorText.slice(0, 2000),
      }),
    },
  );
}

async function dispatchWorkflow(jobId: string): Promise<void> {
  const pat = requireEnv("GITHUB_PAT", GITHUB_PAT);
  const response = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/actions/workflows/${GITHUB_WORKFLOW_ID}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${pat}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ref: GITHUB_REF,
        inputs: {
          job_id: jobId,
        },
      }),
    },
  );

  if (!response.ok) {
    throw new Error(
      `GitHub workflow dispatch failed: ${response.status} ${await response
        .text()}`,
    );
  }
}

Deno.serve(async (request) => {
  if (request.method !== "POST") {
    return json(405, { error: "Method not allowed" });
  }

  const expectedAnonKey = requireEnv("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY);
  const authHeader = request.headers.get("Authorization");
  const apiKey = request.headers.get("apikey");
  const expectedBearer = `Bearer ${expectedAnonKey}`;

  if (authHeader !== expectedBearer || apiKey !== expectedAnonKey) {
    return json(401, { error: "Unauthorized" });
  }

  let payload: { job_id?: string };
  try {
    payload = await request.json();
  } catch {
    return json(400, { error: "Invalid JSON body" });
  }

  const jobId = payload.job_id;
  if (!jobId) {
    return json(400, { error: "job_id is required" });
  }

  try {
    const job = await getPendingJob(jobId);
    if (!job) {
      return json(409, {
        error: "Job must exist in pending state before dispatch",
        job_id: jobId,
      });
    }

    await dispatchWorkflow(jobId);
    await markDispatched(jobId);

    return json(202, { ok: true, job_id: jobId, status: "dispatched" });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    try {
      await markFailed(jobId, message);
    } catch (_) {
      // Keep the original dispatch failure as the response surface.
    }
    return json(500, { error: message, job_id: jobId });
  }
});
