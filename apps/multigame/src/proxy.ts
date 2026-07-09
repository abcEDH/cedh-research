import { NextRequest, NextResponse } from "next/server";
import { resolveTenantSlug } from "@/lib/games/resolve-tenant";

/**
 * Tenant resolution proxy (Next 16 renamed `middleware.ts` to `proxy.ts`).
 *
 * Rewrites every request to the internal /[game]/ tree. Resolution logic
 * lives in `@/lib/games/resolve-tenant` so it stays unit-testable.
 */
export default function proxy(request: NextRequest) {
  const url = request.nextUrl;

  const game = resolveTenantSlug({
    pathname: url.pathname,
    queryGame: url.searchParams.get("game"),
    host: request.headers.get("host"),
  });

  // Already targeting an internal /[game]/ path — pass through.
  if (game === null) {
    return NextResponse.next();
  }

  const rewritten = url.clone();
  rewritten.pathname = `/${game}${url.pathname === "/" ? "" : url.pathname}`;
  return NextResponse.rewrite(rewritten);
}

export const config = {
  // Skip Next internals, API routes, and files with extensions (favicon, images, …).
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
