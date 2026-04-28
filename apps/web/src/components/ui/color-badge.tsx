const COLOR_CLASSES: Record<string, string> = {
  W: "bg-amber-200/80 text-amber-950",
  U: "bg-sky-500/90 text-white",
  B: "bg-purple-900/90 text-purple-100",
  R: "bg-red-500/90 text-white",
  G: "bg-emerald-500/90 text-white",
};

const SIZE_CLASSES: Record<"sm" | "lg", string> = {
  sm: "h-5 w-5 text-[10px]",
  lg: "h-8 w-8 text-sm",
};

export function ColorBadge({
  color,
  size = "sm",
}: {
  color: string;
  size?: "sm" | "lg";
}) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${SIZE_CLASSES[size]} ${
        COLOR_CLASSES[color] ?? "bg-slate-500 text-white"
      }`}
    >
      {color}
    </span>
  );
}
