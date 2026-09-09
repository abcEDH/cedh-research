import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  if (!request.nextUrl.pathname.startsWith("/internal/analytics")) return NextResponse.next();

  const username = process.env.ANALYTICS_DASHBOARD_USERNAME;
  const password = process.env.ANALYTICS_DASHBOARD_PASSWORD;
  if (!username || !password) return new NextResponse("Not found", { status: 404 });

  const authorization = request.headers.get("authorization");
  if (authorization?.startsWith("Basic ")) {
    try {
      const decoded = atob(authorization.slice(6));
      const separator = decoded.indexOf(":");
      if (separator >= 0 && decoded.slice(0, separator) === username && decoded.slice(separator + 1) === password) {
        return NextResponse.next();
      }
    } catch {
      // Treat malformed credentials as unauthenticated.
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="tedh.gg analytics"' },
  });
}

export const config = { matcher: "/internal/analytics/:path*" };
