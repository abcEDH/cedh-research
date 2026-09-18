import Image from "next/image";

const GLOW_COLOR = ["hsl(var(--knd-cyan) / 0.22)", "hsl(var(--knd-magenta) / 0.22)"];

function glowShadow(size: number, index: number) {
  return `0 ${Math.round(size / 6)}px ${Math.round(size / 2.5)}px rgba(2,10,26,0.75), 0 0 ${Math.round(
    size / 2
  )}px ${GLOW_COLOR[index] ?? GLOW_COLOR[0]}`;
}

/**
 * Renders one or two overlapping rounded card-art crops with a glowing shadow —
 * used for commander/partner-pair thumbnails throughout the mobile card-art design.
 * Presentational only: pass resolved image URLs (or null while still loading).
 */
export function ArtCropStack({
  urls,
  size,
  alt = "",
}: {
  urls: Array<string | null | undefined>;
  size: number;
  alt?: string;
}) {
  const items = urls.slice(0, 2);
  const overlap = Math.round(size * 0.58);
  const width = items.length > 1 ? size + overlap : size;

  return (
    <div className="relative shrink-0" style={{ width, height: size }}>
      {items.map((url, index) => (
        <div
          key={index}
          className="absolute overflow-hidden rounded-xl border border-border/60 bg-muted"
          style={{
            width: size,
            height: size,
            top: 0,
            left: index === 0 ? 0 : overlap,
            boxShadow: glowShadow(size, index),
          }}
        >
          {url && (
            <Image
              src={url}
              alt={alt}
              width={size}
              height={size}
              className="h-full w-full object-cover object-[50%_32%]"
              unoptimized
              loading="lazy"
            />
          )}
        </div>
      ))}
    </div>
  );
}
