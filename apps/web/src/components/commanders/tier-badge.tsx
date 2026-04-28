import { Badge } from "@/components/ui/badge";

const TIER_CLASSES: Record<string, string> = {
  core: "bg-[hsl(var(--knd-cyan))]/15 text-primary border-primary/30",
  essential: "bg-[hsl(var(--knd-cyan))]/10 text-primary border-primary/20",
  common: "bg-[hsl(var(--knd-amber))]/15 text-[hsl(var(--knd-amber))] border-[hsl(var(--knd-amber))]/30",
  flex: "bg-muted/40 text-muted-foreground border-border/60",
  spice: "bg-muted/30 text-muted-foreground border-border/40",
};

export function TierBadge({ tier }: { tier: string }) {
  return (
    <Badge
      variant="outline"
      className={TIER_CLASSES[tier] ?? "bg-muted/30 text-muted-foreground border-border/40"}
    >
      {tier}
    </Badge>
  );
}
