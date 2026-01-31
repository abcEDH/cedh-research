import { Suspense } from "react";
import SurvivalClient from "./SurvivalClient";

export const dynamic = "force-dynamic";

export default function SurvivalPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-muted-foreground">Loading survival data...</p>
        </div>
      }
    >
      <SurvivalClient />
    </Suspense>
  );
}
