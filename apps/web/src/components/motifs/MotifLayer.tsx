import Image from "next/image";
import * as React from "react";

function MotifImage({
  src,
  className,
}: {
  src: string;
  className: string;
}) {
  return (
    <div className={className}>
      <Image alt="" fill sizes="100vw" src={src} className="object-contain" />
    </div>
  );
}

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
      <MotifImage src="/motifs/gridlines.svg" className="absolute inset-0 opacity-[0.12] mix-blend-screen" />
      <MotifImage src="/motifs/particles.svg" className="absolute inset-0 opacity-[0.2] mix-blend-screen" />

      {variant === "A" && (
        <MotifImage
          src="/motifs/canopy-corner.svg"
          className="absolute -top-40 -left-40 h-[1100px] w-[1100px] opacity-[0.18] mix-blend-screen"
        />
      )}

      {variant === "B" && (
        <MotifImage
          src="/motifs/transit-arc.svg"
          className="absolute top-28 left-[-22%] h-[1500px] w-[1500px] opacity-[0.18] mix-blend-screen"
        />
      )}

      {variant === "C" && (
        <MotifImage
          src="/motifs/spirit-core.svg"
          className="absolute top-[-20%] left-[2%] h-[1400px] w-[1400px] opacity-[0.28] mix-blend-screen"
        />
      )}

      <MotifImage
        src="/motifs/corner-glyph.svg"
        className="absolute -top-24 -left-24 h-[560px] w-[560px] opacity-[0.10] mix-blend-screen"
      />
      <MotifImage
        src="/motifs/corner-glyph.svg"
        className="absolute -bottom-28 -right-28 h-[560px] w-[560px] rotate-180 opacity-[0.10] mix-blend-screen"
      />
    </div>
  );
}
