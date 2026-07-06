"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { navItems, isNavItemActive } from "@/components/nav-items";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        className="flex size-11 items-center justify-center rounded-[10px] text-muted-foreground transition hover:bg-muted/40 hover:text-foreground md:hidden"
        aria-label="Open navigation menu"
      >
        <Menu className="size-6" />
      </SheetTrigger>
      <SheetContent side="right" className="w-72">
        <SheetHeader>
          <SheetTitle>
            tedh
            <span className="mx-1 inline-block h-1.5 w-1.5 translate-y-[-0.45rem] rounded-full bg-primary" />
            gg
          </SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-1 px-2 text-base text-muted-foreground">
          {navItems.map((item) => {
            const active = isNavItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                className={`flex min-h-11 items-center rounded-[10px] px-4 transition ${
                  active
                    ? "bg-accent/60 font-semibold text-foreground"
                    : "hover:bg-muted/40 hover:text-foreground"
                }`}
                href={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
