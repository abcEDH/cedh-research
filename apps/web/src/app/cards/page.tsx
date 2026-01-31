"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface GlobalCardFrequency {
  card_name: string;
  deck_count: number;
  total_decks: number;
  inclusion_rate: string;
  commander_count: number;
  tier: string;
  top_commanders?: CommanderUsage[];
}

interface CommanderUsage {
  commander_id: string;
  commander: string;
  deck_count: number;
}

const ITEMS_PER_PAGE = 50;

export default function CardsPage() {
  const [cards, setCards] = useState<GlobalCardFrequency[]>([]);
  const [displayCount, setDisplayCount] = useState(ITEMS_PER_PAGE);
  const [loading, setLoading] = useState(true);
  const [tierFilter, setTierFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    async function fetchCards() {
      setLoading(true);

      const { data, error } = await supabase
        .from("card_frequencies_global")
        .select("*")
        .order("inclusion_rate", { ascending: false });

      if (error) {
        console.error("Error fetching card frequencies:", error);
        setLoading(false);
        return;
      }

      const cardData = data as GlobalCardFrequency[];
      const topCardNames = cardData.slice(0, 200).map((c) => c.card_name);
      const commanderUsage = await getCommanderUsageForCards(topCardNames);

      const cardsWithCommanders = cardData.map((card, index) => ({
        ...card,
        top_commanders: index < 200 ? commanderUsage.get(card.card_name) || [] : [],
      }));

      setCards(cardsWithCommanders);
      setLoading(false);
    }

    fetchCards();
  }, []);

  async function getCommanderUsageForCards(
    cardNames: string[]
  ): Promise<Map<string, CommanderUsage[]>> {
    if (cardNames.length === 0) return new Map();

    const { data, error } = await supabase
      .from("card_frequencies_by_commander")
      .select("card_name, commander_id, commander, deck_count")
      .in("card_name", cardNames)
      .order("deck_count", { ascending: false });

    if (error) {
      console.error("Error fetching commander usage:", error);
      return new Map();
    }

    const usageMap = new Map<string, CommanderUsage[]>();
    for (const row of data || []) {
      const existing = usageMap.get(row.card_name) || [];
      if (existing.length < 3) {
        existing.push({
          commander_id: row.commander_id,
          commander: row.commander,
          deck_count: row.deck_count,
        });
        usageMap.set(row.card_name, existing);
      }
    }
    return usageMap;
  }

  const filteredCards = cards.filter((card) => {
    const matchesTier = tierFilter === "all" || card.tier === tierFilter;
    const matchesSearch =
      searchQuery === "" ||
      card.card_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTier && matchesSearch;
  });

  const displayedCards = filteredCards.slice(0, displayCount);
  const hasMore = displayCount < filteredCards.length;

  const tierCounts = {
    core: cards.filter((c) => c.tier === "core").length,
    essential: cards.filter((c) => c.tier === "essential").length,
    common: cards.filter((c) => c.tier === "common").length,
    flex: cards.filter((c) => c.tier === "flex").length,
    spice: cards.filter((c) => c.tier === "spice").length,
  };

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <div className="knd-watermark absolute inset-0" />
          <div className="relative">
            <Link
              href="/"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to Home
            </Link>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              Card Frequency Analysis
            </h1>
            <p className="text-muted-foreground mt-2">
              Global inclusion rates across {cards[0]?.total_decks?.toLocaleString() || 0} analyzed decklists.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-5 mb-8">
          <TierCard tier="Core" count={tierCounts.core} description="80%+" tone="primary" />
          <TierCard tier="Essential" count={tierCounts.essential} description="60-79%" tone="primary" muted />
          <TierCard tier="Common" count={tierCounts.common} description="30-59%" tone="amber" />
          <TierCard tier="Flex" count={tierCounts.flex} description="10-29%" tone="neutral" />
          <TierCard tier="Spice" count={tierCounts.spice} description="<10%" tone="neutral" muted />
        </div>

        <Card className="mb-6">
          <CardHeader className="knd-panel-header">
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Search Cards
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setDisplayCount(ITEMS_PER_PAGE);
                  }}
                  placeholder="Search by card name..."
                  className="knd-input mt-2"
                />
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Filter by Tier
                </label>
                <select
                  value={tierFilter}
                  onChange={(e) => {
                    setTierFilter(e.target.value);
                    setDisplayCount(ITEMS_PER_PAGE);
                  }}
                  className="knd-input mt-2"
                >
                  <option value="all">All Tiers</option>
                  <option value="core">Core (80%+)</option>
                  <option value="essential">Essential (60-79%)</option>
                  <option value="common">Common (30-59%)</option>
                  <option value="flex">Flex (10-29%)</option>
                  <option value="spice">Spice (&lt;10%)</option>
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="knd-panel-header">
            <CardTitle className="text-lg">
              {tierFilter === "all"
                ? "All Cards"
                : `${tierFilter.charAt(0).toUpperCase() + tierFilter.slice(1)} Cards`}{" "}
              ({filteredCards.length.toLocaleString()})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-12 text-muted-foreground">Loading...</div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <TableHead>Rank</TableHead>
                      <TableHead>Card Name</TableHead>
                      <TableHead>Tier</TableHead>
                      <TableHead className="text-right">Inclusion</TableHead>
                      <TableHead className="text-right">Decks</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayedCards.map((card, index) => (
                      <TableRow key={card.card_name} className="border-border/60">
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          #{index + 1}
                        </TableCell>
                        <TableCell className="font-medium">
                          <a
                            href={`https://scryfall.com/search?q=${encodeURIComponent(
                              normalizeDisplayString(card.card_name)
                            )}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-foreground hover:text-primary"
                          >
                            {normalizeDisplayString(card.card_name)}
                          </a>
                        </TableCell>
                        <TableCell>
                          <TierBadge tier={card.tier} />
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {(parseFloat(card.inclusion_rate) * 100).toFixed(1)}%
                        </TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">
                          {card.deck_count.toLocaleString()}/{card.total_decks.toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                <div className="flex flex-col items-center gap-2 mt-6 pt-4 border-t border-border/60">
                  <p className="text-muted-foreground text-sm">
                    Showing {displayedCards.length} of {filteredCards.length} cards
                  </p>
                  {hasMore && (
                    <Button
                      onClick={() => setDisplayCount(displayCount + ITEMS_PER_PAGE)}
                      className="border-border/70 bg-muted/30 text-foreground hover:bg-muted/40"
                    >
                      Load More
                    </Button>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function TierCard({
  tier,
  count,
  description,
  tone,
  muted = false,
}: {
  tier: string;
  count: number;
  description: string;
  tone: "primary" | "amber" | "neutral";
  muted?: boolean;
}) {
  const toneMap: Record<typeof tone, string> = {
    primary: "text-primary",
    amber: "text-[hsl(var(--knd-amber))]",
    neutral: "text-muted-foreground",
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{tier}</p>
        <p className={`text-2xl font-semibold ${muted ? "text-muted-foreground" : toneMap[tone]}`}>
          {count}
        </p>
        <p className="text-xs text-muted-foreground">{description} inclusion</p>
      </CardContent>
    </Card>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const tierColors: Record<string, string> = {
    core: "bg-[hsl(var(--knd-cyan))]/15 text-primary border-primary/30",
    essential: "bg-[hsl(var(--knd-cyan))]/10 text-primary border-primary/20",
    common: "bg-[hsl(var(--knd-amber))]/15 text-[hsl(var(--knd-amber))] border-[hsl(var(--knd-amber))]/30",
    flex: "bg-muted/40 text-muted-foreground border-border/60",
    spice: "bg-muted/30 text-muted-foreground border-border/40",
  };

  return (
    <Badge
      variant="outline"
      className={tierColors[tier] || "bg-muted/30 text-muted-foreground border-border/40"}
    >
      {tier}
    </Badge>
  );
}
