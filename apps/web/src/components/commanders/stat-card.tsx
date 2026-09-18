import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export function StatCard({
  label,
  value,
  tone,
  tooltip,
}: {
  label: string;
  value: string;
  tone: "primary" | "amber" | "neutral";
  tooltip?: string;
}) {
  const toneMap: Record<typeof tone, string> = {
    primary: "text-primary",
    amber: "text-[hsl(var(--knd-amber))]",
    neutral: "text-muted-foreground",
  };

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-2">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
          {tooltip && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="text-[10px] text-muted-foreground/80 hover:text-foreground"
                  aria-label={`More info about ${label}`}
                >
                  i
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs leading-relaxed">
                {tooltip}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <p className={`${value.length > 12 ? "text-lg" : "text-xl"} font-semibold ${toneMap[tone]}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

export function ColorBadge({ color, size = "sm" }: { color: string; size?: "sm" | "lg" }) {
  const colors: Record<string, string> = {
    W: "bg-amber-200/80 text-amber-950",
    U: "bg-sky-500/90 text-white",
    B: "bg-purple-900/90 text-purple-100",
    R: "bg-red-500/90 text-white",
    G: "bg-emerald-500/90 text-white",
  };

  const sizeClass = size === "lg" ? "w-8 h-8 text-sm" : "w-5 h-5 text-xs";

  return (
    <span
      className={`${sizeClass} rounded-full flex items-center justify-center font-bold ${
        colors[color] || "bg-slate-500 text-white"
      }`}
    >
      {color}
    </span>
  );
}
