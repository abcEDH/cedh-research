import { Coffee, HandHeart, Mail, MessageCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

export function SupportBanner() {
  return (
    <aside
      aria-labelledby="support-banner-title"
      className="border-t border-border/60 px-4 py-6"
    >
      <div className="container mx-auto flex max-w-5xl flex-col items-center gap-4 text-center sm:flex-row sm:justify-between sm:text-left">
        <div className="max-w-xl">
          <h2 id="support-banner-title" className="text-base font-semibold text-foreground">
            Help keep tedh.gg running
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Community support helps cover the costs of keeping this resource free for cEDH players.
          </p>
        </div>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
          <Button asChild variant="ghost" className="h-11 w-full text-muted-foreground hover:text-foreground sm:w-auto">
            <a href="mailto:contact@tedh.gg">
              <Mail />
              Contact Us
            </a>
          </Button>
          <Button asChild variant="ghost" className="h-11 w-full text-muted-foreground hover:text-foreground sm:w-auto">
            <a href="https://discord.gg/MZCkEakB3d" target="_blank" rel="noreferrer">
              <MessageCircle />
              Discord
            </a>
          </Button>
          <Button asChild variant="ghost" className="h-11 w-full text-muted-foreground hover:text-foreground sm:w-auto">
            <a
              href="https://www.patreon.com/cw/tedh_gg"
              target="_blank"
              rel="noreferrer"
            >
              <HandHeart />
              Support on Patreon
            </a>
          </Button>
          <Button asChild variant="ghost" className="h-11 w-full text-muted-foreground hover:text-foreground sm:w-auto">
            <a
              href="https://buymeacoffee.com/tedh_gg"
              target="_blank"
              rel="noreferrer"
            >
              <Coffee />
              Buy Me a Coffee
            </a>
          </Button>
        </div>
      </div>
    </aside>
  );
}
