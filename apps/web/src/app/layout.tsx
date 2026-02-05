import type { Metadata } from "next";
import "./globals.css";
import { MotifLayer } from "@/components/motifs/MotifLayer";

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
        {children}
      </body>
    </html>
  );
}
