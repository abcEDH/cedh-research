import type { GameSlug } from "@/lib/games/registry";

/**
 * Build an internal href that preserves the current tenant.
 *
 * The proxy resolves a tenant from (in order) an internal /[game]/ path
 * prefix, a `?game=` query override, then the request hostname
 * (src/lib/games/resolve-tenant.ts). On a real subdomain the hostname alone
 * is enough, but on local dev or a Vercel preview the tenant only exists as
 * a `?game=` override — and since the proxy rewrite is invisible to the
 * browser, every outgoing link must carry that override forward itself or
 * the next navigation silently falls back to the default tenant (PR #247
 * review). Appending `?game=<slug>` unconditionally is a no-op on real
 * subdomains and correct everywhere else.
 */
export function withGameParam(
  path: string,
  slug: GameSlug,
  extraParams?: Record<string, string>
): string {
  const [pathname, existingQuery] = path.split("?");
  const params = new URLSearchParams(existingQuery);
  params.set("game", slug);
  for (const [key, value] of Object.entries(extraParams ?? {})) {
    params.set(key, value);
  }
  return `${pathname}?${params.toString()}`;
}
