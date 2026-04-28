import type { Metadata } from "next";
import "./globals.css";
import { MotifLayer } from "@/components/motifs/MotifLayer";

export const metadata: Metadata = {
  title: "tedh.gg",
  description: "tedh.gg for competitive Commander. Track commander performance, card trends, and tournament results.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap"
        />
      </head>
      <body
        className="knd-body"
      >
        <MotifLayer variant="B" intensity={0.9} />
        <div className="flex min-h-screen flex-col">
          <div className="flex-1">{children}</div>
          <footer className="border-t border-border/60 px-4 py-4 text-center text-xs text-muted-foreground">
            Data provided by{" "}
            <a
              href="https://topdeck.gg"
              target="_blank"
              rel="noreferrer"
              className="text-foreground hover:text-primary"
            >
              TopDeck.gg
            </a>
          </footer>
        </div>
      </body>
    </html>
  );
}
