'use client';

import * as React from 'react';
import { MotifLayer } from '@/components/motifs/MotifLayer';

type Variant = 'A' | 'B' | 'C';

/**
 * Global motif overlay toggle for design review.
 * Mount it in app/layout.tsx under <body>.
 */
export function MotifDebugOverlay({
  initialEnabled = true,
  initialVariant = 'B',
  initialIntensity = 0.9,
}: {
  initialEnabled?: boolean;
  initialVariant?: Variant;
  initialIntensity?: number;
}) {
  const [enabled, setEnabled] = React.useState(initialEnabled);
  const [variant, setVariant] = React.useState<Variant>(initialVariant);
  const [intensity, setIntensity] = React.useState(initialIntensity);

  return (
    <>
      {enabled ? <MotifLayer variant={variant} intensity={intensity} /> : null}

      <div className="fixed bottom-4 right-4 z-50 knd-panel w-[320px] p-3">
        <div className="flex items-center justify-between">
          <div className="knd-chip">Motif Overlay</div>
          <button
            className="rounded-md border border-border/70 bg-muted/30 px-2 py-1 text-xs hover:bg-muted/40"
            onClick={() => setEnabled((v) => !v)}
            type="button"
          >
            {enabled ? 'Hide' : 'Show'}
          </button>
        </div>

        <div className="mt-3 grid gap-3">
          <div className="flex gap-2">
            {(['A','B','C'] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setVariant(v)}
                className={[
                  'rounded-full border px-2 py-1 text-[11px] transition',
                  variant === v
                    ? 'border-primary/60 bg-primary/15 text-foreground'
                    : 'border-border/70 bg-muted/20 text-muted-foreground hover:bg-muted/30 hover:text-foreground',
                ].join(' ')}
              >
                {v}
              </button>
            ))}
          </div>

          <label className="grid gap-2 text-[11px] text-muted-foreground">
            Intensity <span className="font-mono text-foreground">{intensity.toFixed(2)}</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={intensity}
              onChange={(e) => setIntensity(parseFloat(e.target.value))}
              className="w-full accent-[hsl(var(--knd-cyan))]"
            />
          </label>

          <p className="text-[11px] text-muted-foreground">
            Tip: keep intensity ≤ 0.25 on dense chart pages.
          </p>
        </div>
      </div>
    </>
  );
}
