import type { Metadata, Viewport } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { PostHogProvider } from "./providers";
import { WebVitals } from "./web-vitals";
import { MotifLayer } from "@/components/motifs/MotifLayer";
import { SiteHeader } from "@/components/site-header";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

const SITE_DESCRIPTION =
  "tedh.gg for competitive Commander. Track commander performance, card trends, and tournament results.";

export const metadata: Metadata = {
  metadataBase: new URL("https://tedh.gg"),
  title: "tedh.gg",
  description: SITE_DESCRIPTION,
  appleWebApp: {
    capable: true,
    title: "tedh.gg",
    statusBarStyle: "black-translucent",
  },
  openGraph: {
    title: "tedh.gg",
    description: SITE_DESCRIPTION,
    url: "https://tedh.gg",
    siteName: "tedh.gg",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#030915",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${spaceGrotesk.variable} ${jetBrainsMono.variable}`}>
      <body className="knd-body">
        <PostHogProvider>
          <WebVitals />
          <MotifLayer variant="B" intensity={0.9} />
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
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
        </PostHogProvider>
      </body>
    </html>
  );
}
