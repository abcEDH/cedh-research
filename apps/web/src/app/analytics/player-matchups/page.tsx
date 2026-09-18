import { Metadata } from "next";
import { PlayerMatchupsExport } from "@/components/analytics/player-matchups-export";

export const metadata: Metadata = {
  title: "Player Matchup Analysis | cEDH Analytics",
  description: "Export and analyze head-to-head player matchup data",
};

export default function PlayerMatchupsPage() {
  return <PlayerMatchupsExport />;
}
