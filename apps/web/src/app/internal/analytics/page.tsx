import { notFound } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchDashboardData } from "@/lib/analytics/dashboard";

export const dynamic = "force-dynamic";

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

export default async function InternalAnalyticsPage() {
  if (!process.env.POSTHOG_PERSONAL_API_KEY || !process.env.POSTHOG_PROJECT_ID) notFound();

  let data;
  try {
    data = await fetchDashboardData();
  } catch {
    return <main className="container mx-auto max-w-3xl px-4 py-12"><Card><CardHeader><CardTitle>Analytics unavailable</CardTitle></CardHeader><CardContent className="text-muted-foreground">PostHog could not be queried right now. Check the server credentials and query host.</CardContent></Card></main>;
  }

  return (
    <main className="container mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8"><p className="font-mono text-xs uppercase tracking-[0.2em] text-primary">Internal</p><h1 className="mt-2 text-3xl font-semibold">Usage analytics</h1><p className="mt-2 text-muted-foreground">Last 30 days · aggregate PostHog data</p></div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Pageviews" value={data.summary.pageviews} />
        <Metric label="Unique visitors" value={data.summary.uniqueUsers} />
        <Metric label="Sessions" value={data.summary.sessions} />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card><CardHeader><CardTitle>Daily traffic</CardTitle></CardHeader><CardContent><div className="space-y-3">{data.daily.map((item) => <div key={item.day} className="grid grid-cols-[5rem_1fr_4rem] items-center gap-3 text-sm"><span className="text-muted-foreground">{item.day.slice(5)}</span><div className="h-2 rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(3, Math.round((item.pageviews / Math.max(...data.daily.map((day) => day.pageviews), 1)) * 100))}%` }} /></div><span className="text-right font-mono text-xs">{formatNumber(item.pageviews)}</span></div>)}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>Device mix</CardTitle></CardHeader><CardContent className="space-y-3">{data.devices.map((item) => <div key={item.device} className="flex items-center justify-between border-b border-border/50 pb-2 text-sm last:border-0"><span>{item.device}</span><span className="font-mono text-muted-foreground">{formatNumber(item.pageviews)}</span></div>)}</CardContent></Card>
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <AnalyticsTable title="Top pages" headers={["Path", "Views", "Visitors"]} rows={data.topPages.map((item) => [item.path, formatNumber(item.pageviews), formatNumber(item.uniqueUsers)])} />
        <AnalyticsTable title="Top actions" headers={["Event", "Count"]} rows={data.topActions.map((item) => [item.event, formatNumber(item.count)])} />
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) { return <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold text-primary">{formatNumber(value)}</p></CardContent></Card>; }
function AnalyticsTable({ title, headers, rows }: { title: string; headers: string[]; rows: string[][] }) { return <Card><CardHeader><CardTitle>{title}</CardTitle></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-border/60 text-muted-foreground">{headers.map((header) => <th key={header} className="pb-2 pr-4 font-medium">{header}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.join("-")} className="border-b border-border/40 last:border-0">{row.map((cell, index) => <td key={`${cell}-${index}`} className="max-w-[18rem] truncate py-2 pr-4 font-mono text-xs">{cell}</td>)}</tr>)}</tbody></table></div></CardContent></Card>; }
