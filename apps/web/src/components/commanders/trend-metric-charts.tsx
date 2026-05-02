"use client";

import { useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TrendMetricPoint = {
  period: string;
  entries: number;
  winRate: number | null;
  pointsPerGame: number | null;
};

export type TrendMetricSeries = {
  weekly: TrendMetricPoint[];
  monthly: TrendMetricPoint[];
};

function MetricChart({
  data,
  dataKey,
  label,
  formatter,
}: {
  data: TrendMetricPoint[];
  dataKey: keyof TrendMetricPoint;
  label: string;
  formatter: (value: number) => string;
}) {
  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg border border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
        No data available.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/60 bg-card/50 p-3">
      <div className="mb-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
            <XAxis
              dataKey="period"
              tick={{ fill: "#9FB3D9", fontSize: 11 }}
              tickFormatter={(value) => formatPeriod(value)}
            />
            <YAxis tick={{ fill: "#9FB3D9", fontSize: 11 }} width={40} />
            <Tooltip
              formatter={(value) => {
                if (value === null || value === undefined) return "—";
                const numeric = Number(value);
                return Number.isFinite(numeric) ? formatter(numeric) : "—";
              }}
              contentStyle={{
                background: "#0B0F1A",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "#9FB3D9" }}
            />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke="#46F2F2"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function TrendMetricCharts({
  series,
  title,
  description,
}: {
  series: TrendMetricSeries;
  title: string;
  description?: string;
}) {
  const [range, setRange] = useState<"weekly" | "monthly">("monthly");

  const data = useMemo(() => (range === "weekly" ? series.weekly : series.monthly), [range, series]);

  return (
    <div className="rounded-2xl border border-border/60 bg-card/60 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Trendlines</p>
          <p className="text-lg font-semibold text-foreground">{title}</p>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setRange("weekly")}
            className={`rounded-full border px-3 py-1 ${
              range === "weekly"
                ? "border-primary/50 text-foreground"
                : "border-border/60 text-muted-foreground"
            }`}
          >
            Weekly
          </button>
          <button
            type="button"
            onClick={() => setRange("monthly")}
            className={`rounded-full border px-3 py-1 ${
              range === "monthly"
                ? "border-primary/50 text-foreground"
                : "border-border/60 text-muted-foreground"
            }`}
          >
            Monthly
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <MetricChart
          data={data}
          dataKey="entries"
          label="Entries"
          formatter={(value) => value.toLocaleString()}
        />
        <MetricChart
          data={data}
          dataKey="winRate"
          label="Win Rate %"
          formatter={(value) => `${value.toFixed(1)}%`}
        />
        <MetricChart
          data={data}
          dataKey="pointsPerGame"
          label="Avg Points / Game"
          formatter={(value) => value.toFixed(2)}
        />
      </div>
    </div>
  );
}

function formatPeriod(value: string) {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [, month, day] = value.split("-").map(Number);
    if (!month || !day) return value;
    return `${month}/${day}`;
  }
  if (/^\d{4}-\d{2}$/.test(value)) {
    const [year, month] = value.split("-").map(Number);
    if (!month) return value;
    const shortYear = year % 100;
    return `${month}/${shortYear.toString().padStart(2, "0")}`;
  }
  return value;
}
