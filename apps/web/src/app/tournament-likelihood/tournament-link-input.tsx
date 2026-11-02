"use client";

import type { InputHTMLAttributes } from "react";
import { extractTopDeckTournamentUrl } from "@/lib/topdeck-input";

export function TournamentLinkInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      onPaste={(event) => {
        const url = extractTopDeckTournamentUrl(event.clipboardData.getData("text/plain"));
        if (!url) return;
        event.preventDefault();
        event.currentTarget.value = url;
      }}
    />
  );
}
