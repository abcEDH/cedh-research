"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MobileNav } from "@/components/mobile-nav";
import { navItems, isNavItemActive } from "@/components/nav-items";

// Note: "/commanders" is intentionally omitted from the nav — the commander
// rankings page stays reachable by URL but is deprioritized in the header.
const navItems = [
  { href: "/tournaments", label: "Tournaments" },
  { href: "/regional-elo", label: "Leaderboard" },
  { href: "/tournament-likelihood", label: "Tournament Prep" },
  { href: "/about", label: "Methodology" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/80 pt-[env(safe-area-inset-top)] backdrop-blur-xl">
      <div className="container mx-auto flex flex-row items-center justify-between gap-4 px-4 py-3 md:py-4">
        <Link href="/" aria-label="tedh.gg" className="text-xl font-semibold text-foreground transition hover:text-primary">
          tedh<span className="mx-1 inline-block h-1.5 w-1.5 translate-y-[-0.45rem] rounded-full bg-primary" />gg
        </Link>
        <nav className="hidden flex-wrap items-center gap-1 text-sm text-muted-foreground md:flex">
          {navItems.map((item) => {
            const active = isNavItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                className={`rounded-[10px] px-3.5 py-2 transition ${
                  active ? "bg-accent/60 font-semibold text-foreground" : "hover:bg-muted/40 hover:text-foreground"
                }`}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <MobileNav />
      </div>
    </header>
  );
}
