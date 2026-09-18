// Note: "/commanders" is intentionally omitted from the nav — the commander
// rankings page stays reachable by URL but is deprioritized in the header and
// mobile menu. Both SiteHeader and MobileNav consume this shared list.
export const navItems = [
  { href: "/tournaments", label: "Tournaments" },
  { href: "/regional-elo", label: "Leaderboard" },
  { href: "/tournament-likelihood", label: "Tournament Prep" },
  { href: "/about", label: "Methodology" },
] as const;

export function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
