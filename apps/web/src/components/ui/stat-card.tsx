import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

type Tone = "primary" | "amber" | "neutral";

const TONE_CLASSES: Record<Tone, string> = {
  primary: "text-primary",
  amber: "text-[hsl(var(--knd-amber))]",
  neutral: "text-muted-foreground",
};

export function StatCard({
  label,
  value,
  tone,
  tooltip,
  testId,
}: {
  label: string;
  value: string;
  tone: Tone;
  tooltip?: string;
  testId?: string;
}) {
  return (
    <Card>
      <CardContent className="pb-4 pt-4">
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
        <p data-testid={testId} className={`text-2xl font-semibold ${TONE_CLASSES[tone]}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
