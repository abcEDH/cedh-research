import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import { MotifLayer } from "@/components/motifs/MotifLayer";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "cEDH Analytics",
  description: "Data-driven insights for competitive Commander. Track commander performance, card frequencies, and meta trends.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} dark`}>
      <body className="knd-body">
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
