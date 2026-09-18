import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "tedh.gg",
    short_name: "tedh.gg",
    description:
      "tedh.gg for competitive Commander. Track commander performance, card trends, and tournament results.",
    start_url: "/",
    display: "standalone",
    background_color: "#030915",
    theme_color: "#030915",
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
