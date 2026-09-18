import * as React from "react";
import Image from "next/image";

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
      <Image
        src="/motifs/gridlines.svg"
        fill
        className="opacity-[0.12] mix-blend-screen object-cover"
        alt=""
        priority
        unoptimized
      />
      <Image
        src="/motifs/particles.svg"
        fill
        className="opacity-[0.2] mix-blend-screen object-cover"
        alt=""
        priority
        unoptimized
      />

      {/* Large decorative blobs are hidden below md: — they cost real paint
          time on phones for a barely visible effect. */}
      {variant === "A" && (
        <div className="absolute -top-40 -left-40 hidden h-[1100px] w-[1100px] opacity-[0.18] mix-blend-screen md:block">
          <Image
            src="/motifs/canopy-corner.svg"
            fill
            alt=""
            unoptimized
          />
        </div>
      )}

      {variant === "B" && (
        <div className="absolute top-28 left-[-22%] hidden h-[1500px] w-[1500px] opacity-[0.18] mix-blend-screen md:block">
          <Image
            src="/motifs/transit-arc.svg"
            fill
            alt=""
            unoptimized
          />
        </div>
      )}

      {variant === "C" && (
        <div className="absolute top-[-20%] left-[2%] hidden h-[1400px] w-[1400px] opacity-[0.28] mix-blend-screen md:block">
          <Image
            src="/motifs/spirit-core.svg"
            fill
            alt=""
            unoptimized
          />
        </div>
      )}

      <div className="absolute -top-24 -left-24 h-[560px] w-[560px] opacity-[0.10] mix-blend-screen">
        <Image
          src="/motifs/corner-glyph.svg"
          fill
          alt=""
          unoptimized
        />
      </div>
      <div className="absolute -bottom-28 -right-28 h-[560px] w-[560px] rotate-180 opacity-[0.10] mix-blend-screen">
        <Image
          src="/motifs/corner-glyph.svg"
          fill
          alt=""
          unoptimized
        />
      </div>
    </div>
  );
}
