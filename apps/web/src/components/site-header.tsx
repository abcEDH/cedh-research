"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/tournaments", label: "Tournaments" },
  { href: "/commanders", label: "Commanders" },
  { href: "/regional-elo", label: "Leaderboard" },
  { href: "/tournament-likelihood", label: "Tournament Prep" },
  { href: "/about", label: "Methodology" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/80 backdrop-blur-xl">
      <div className="container mx-auto flex flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
        <Link href="/" aria-label="tedh.gg" className="text-xl font-semibold text-foreground transition hover:text-primary">
          tedh<span className="mx-1 inline-block h-1.5 w-1.5 translate-y-[-0.45rem] rounded-full bg-primary" />gg
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
          {navItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
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
      </div>
    </header>
  );
}
