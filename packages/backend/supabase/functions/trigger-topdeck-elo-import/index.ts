const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY");
const GITHUB_PAT = Deno.env.get("GITHUB_PAT");
const GITHUB_OWNER = Deno.env.get("GITHUB_OWNER") ?? "abcEDH";
const GITHUB_REPO = Deno.env.get("GITHUB_REPO") ?? "cedh-research";
const GITHUB_WORKFLOW_ID = Deno.env.get("GITHUB_WORKFLOW_ID") ??
  "topdeck-elo-import.yml";
const GITHUB_REF = Deno.env.get("GITHUB_REF") ?? "main";

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

async function dispatchWorkflow(eloUrl?: string): Promise<void> {
  const pat = requireEnv("GITHUB_PAT", GITHUB_PAT);
  const body: Record<string, unknown> = { ref: GITHUB_REF };
  if (eloUrl) {
    body.inputs = { elo_url: eloUrl };
  }

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
      body: JSON.stringify(body),
    },
  );

  if (!response.ok) {
    throw new Error(
      `GitHub workflow dispatch failed: ${response.status} ${await response.text()}`,
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

  let payload: { elo_url?: string } = {};
  try {
    const text = await request.text();
    if (text.trim()) {
      payload = JSON.parse(text);
    }
  } catch {
    return json(400, { error: "Invalid JSON body" });
  }

  try {
    await dispatchWorkflow(payload.elo_url);
    return json(202, {
      ok: true,
      status: "dispatched",
      workflow: GITHUB_WORKFLOW_ID,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return json(500, { error: message });
  }
});
