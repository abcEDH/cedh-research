export const navItems = [
  { href: "/tournaments", label: "Tournaments" },
  { href: "/commanders", label: "Commanders" },
  { href: "/regional-elo", label: "Leaderboard" },
  { href: "/tournament-likelihood", label: "Tournament Prep" },
  { href: "/about", label: "Methodology" },
] as const;

export function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
