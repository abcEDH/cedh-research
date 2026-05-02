"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

export type CommanderTrendSeriesPoint = {
  week: string;
  [commanderId: string]: number | string | null;
};

export type CommanderTrendSeriesMeta = {
  id: string;
  name: string;
};

const COLORS = [
  "#46F2F2",
  "#FF4FD8",
  "#6B4CFF",
  "#2B5CFF",
  "#9FB3D9",
  "#4DD4AC",
  "#F5A524",
  "#FF7A7A",
  "#7CFF6B",
  "#D38BFF",
];

export default function CommanderTrendsChart({
  data,
  series,
  yLabel = "Win Rate (%)",
  title = "Top 10 commanders over time",
  description = "Weekly win rate trends (last 13 weeks).",
}: {
  data: CommanderTrendSeriesPoint[];
  series: CommanderTrendSeriesMeta[];
  yLabel?: string;
  title?: string;
  description?: string;
}) {
  const colorMap = useMemo(() => {
    const map = new Map<string, string>();
    series.forEach((item, index) => {
      map.set(item.id, COLORS[index % COLORS.length]);
    });
    return map;
  }, [series]);

  if (!data || data.length === 0 || series.length === 0) {
    return (
      <div className="rounded-lg border border-border/60 bg-muted/20 p-6 text-sm text-muted-foreground">
        No win rate trend data available.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border/60 bg-card/60 p-4">
      <div className="mb-4">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Trendline</p>
        <p className="text-lg font-semibold text-foreground">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
            <XAxis
              dataKey="week"
              tick={{ fill: "#9FB3D9", fontSize: 12 }}
              tickFormatter={(value) => formatShortDate(value)}
            />
            <YAxis
              tick={{ fill: "#9FB3D9", fontSize: 12 }}
              tickFormatter={(value) => `${value}%`}
              width={44}
              label={{ value: yLabel, angle: -90, position: "insideLeft", fill: "#9FB3D9" }}
            />
            <Tooltip
              formatter={(value) => {
                if (value === null || value === undefined) return "—";
                const numeric = Number(value);
                return Number.isFinite(numeric) ? `${numeric.toFixed(1)}%` : "—";
              }}
              contentStyle={{
                background: "#0B0F1A",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ color: "#9FB3D9" }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "#9FB3D9" }} />
            {series.map((item) => (
              <Line
                key={item.id}
                type="monotone"
                dataKey={item.id}
                name={item.name}
                stroke={colorMap.get(item.id) ?? "#9FB3D9"}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function formatShortDate(value: string) {
  if (!value) return "";
  if (/^\\d{4}-\\d{2}-\\d{2}$/.test(value)) {
    const [_year, month, day] = value.split("-").map(Number);
    if (!month || !day) return value;
    return `${month}/${day}`;
  }
  return value;
}
