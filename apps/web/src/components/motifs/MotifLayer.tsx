import * as React from "react";

export function MotifLayer({
  variant = "B",
  intensity = 0.9,
  className,
}: {
  variant?: "A" | "B" | "C";
  intensity?: number; // 0..1
  className?: string;
}) {
  const opacity = Math.max(0, Math.min(1, intensity));

  return (
    <div
      aria-hidden
      className={[
        "pointer-events-none fixed inset-0 -z-10 overflow-hidden",
        className ?? "",
      ].join(" ")}
      style={{ opacity }}
    >
      <img
        src="/motifs/gridlines.svg"
        className="absolute inset-0 h-full w-full opacity-[0.12] mix-blend-screen"
        alt=""
      />
      <img
        src="/motifs/particles.svg"
        className="absolute inset-0 h-full w-full opacity-[0.2] mix-blend-screen"
        alt=""
      />

      {variant === "A" && (
        <img
          src="/motifs/canopy-corner.svg"
          className="absolute -top-40 -left-40 w-[1100px] opacity-[0.18] mix-blend-screen"
          alt=""
        />
      )}

      {variant === "B" && (
        <img
          src="/motifs/transit-arc.svg"
          className="absolute top-28 left-[-22%] w-[1500px] opacity-[0.18] mix-blend-screen"
          alt=""
        />
      )}

      {variant === "C" && (
        <img
          src="/motifs/spirit-core.svg"
          className="absolute top-[-20%] left-[2%] w-[1400px] opacity-[0.28] mix-blend-screen"
          alt=""
        />
      )}

      <img
        src="/motifs/corner-glyph.svg"
        className="absolute -top-24 -left-24 w-[560px] opacity-[0.10] mix-blend-screen"
        alt=""
      />
      <img
        src="/motifs/corner-glyph.svg"
        className="absolute -bottom-28 -right-28 w-[560px] rotate-180 opacity-[0.10] mix-blend-screen"
        alt=""
      />
    </div>
  );
}
