import "server-only";

type HogQLRow = Array<string | number | null>;

type HogQLResponse = {
  results?: HogQLRow[];
  columns?: string[];
};

export type DashboardData = {
  summary: {
    pageviews: number;
    uniqueUsers: number;
    sessions: number;
  };
  daily: Array<{ day: string; pageviews: number; uniqueUsers: number }>;
  topPages: Array<{ path: string; pageviews: number; uniqueUsers: number }>;
  devices: Array<{ device: string; pageviews: number }>;
  topActions: Array<{ event: string; count: number }>;
};

const POSTHOG_API_HOST = (process.env.POSTHOG_API_HOST || "https://us.posthog.com").replace(/\/$/, "");

function numberAt(row: HogQLRow | undefined, index: number) {
  const value = row?.[index];
  return typeof value === "number" ? value : Number(value || 0);
}

function stringAt(row: HogQLRow | undefined, index: number, fallback = "Unknown") {
  const value = row?.[index];
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

async function runHogQL(query: string): Promise<HogQLResponse> {
  const apiKey = process.env.POSTHOG_PERSONAL_API_KEY;
  const projectId = process.env.POSTHOG_PROJECT_ID;
  if (!apiKey || !projectId) throw new Error("PostHog dashboard credentials are not configured");

  const response = await fetch(`${POSTHOG_API_HOST}/api/projects/${projectId}/query/`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: { kind: "HogQLQuery", query } }),
    next: { revalidate: 300 },
  });

  if (!response.ok) throw new Error(`PostHog query failed (${response.status})`);
  return (await response.json()) as HogQLResponse;
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const [summary, daily, topPages, devices, topActions] = await Promise.all([
    runHogQL(`
      SELECT countIf(event = '$pageview') AS pageviews,
        uniq(distinct_id) AS unique_users,
        uniq(properties.$session_id) AS sessions
      FROM events
      WHERE timestamp >= now() - INTERVAL 30 DAY
    `),
    runHogQL(`
      SELECT toDate(timestamp) AS day, count() AS pageviews,
        uniq(distinct_id) AS unique_users
      FROM events
      WHERE event = '$pageview' AND timestamp >= now() - INTERVAL 30 DAY
      GROUP BY day ORDER BY day
    `),
    runHogQL(`
      SELECT if(properties.$pathname != '', properties.$pathname, properties.path) AS path,
        count() AS pageviews, uniq(distinct_id) AS unique_users
      FROM events
      WHERE event = '$pageview' AND timestamp >= now() - INTERVAL 30 DAY
      GROUP BY path ORDER BY pageviews DESC LIMIT 10
    `),
    runHogQL(`
      SELECT if(properties.$device_type != '', properties.$device_type, 'Unknown') AS device,
        count() AS pageviews
      FROM events
      WHERE event = '$pageview' AND timestamp >= now() - INTERVAL 30 DAY
      GROUP BY device ORDER BY pageviews DESC
    `),
    runHogQL(`
      SELECT event, count() AS count
      FROM events
      WHERE timestamp >= now() - INTERVAL 30 DAY
        AND event NOT IN ('$pageview', '$pageleave', '$autocapture')
      GROUP BY event ORDER BY count DESC LIMIT 10
    `),
  ]);

  return {
    summary: {
      pageviews: numberAt(summary.results?.[0], 0),
      uniqueUsers: numberAt(summary.results?.[0], 1),
      sessions: numberAt(summary.results?.[0], 2),
    },
    daily: (daily.results ?? []).map((row) => ({
      day: stringAt(row, 0), pageviews: numberAt(row, 1), uniqueUsers: numberAt(row, 2),
    })),
    topPages: (topPages.results ?? []).map((row) => ({
      path: stringAt(row, 0), pageviews: numberAt(row, 1), uniqueUsers: numberAt(row, 2),
    })),
    devices: (devices.results ?? []).map((row) => ({ device: stringAt(row, 0), pageviews: numberAt(row, 1) })),
    topActions: (topActions.results ?? []).map((row) => ({ event: stringAt(row, 0), count: numberAt(row, 1) })),
  };
}
