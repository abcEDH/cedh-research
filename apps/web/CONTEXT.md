# cEDH Research - Development Context

## Project Overview
A Next.js 14 dashboard for competitive Magic: The Gathering (cEDH) tournament analytics, consuming data from a Supabase PostgreSQL backend with pre-computed materialized views.

**Live Site:** https://tedh.gg
**Backend Repo:** ~/Documents/Repositories/personal/cedh-research

## Tech Stack
- **Framework:** Next.js 16 (App Router, TypeScript)
- **Styling:** Tailwind CSS + shadcn/ui components
- **Database:** Supabase (PostgreSQL with materialized views)
- **Deployment:** Vercel
- **Charts:** Recharts

## Database Views Available
| View | Description | Used In |
|------|-------------|---------|
| `commander_stats` | Commander performance summary | /commanders, / |
| `card_frequencies_by_commander` | Per-commander card rates | /commanders/[id] |
| `commander_card_report` | Cards with synergy scores | /commanders/[id] |
| `card_performance_by_commander` | Win rate correlation | /commanders/[id] |
| `card_performance_global` | Global card win rates | Internal analysis |
| `trap_cards_report` | Popular underperformers | /trap-spice |
| `spice_cards_report` | Rare overperformers | /trap-spice |
| `commander_head_to_head` | Matchup data | Planned (empty) |
| `commander_meta_share` | Meta representation | Planned |
| `commander_momentum` | Trending commanders | Planned |
| `commander_monthly_trends` | Time series | Planned |
| `player_tournament_journey` | Player progression | Planned |
| `pod_composition` | Pod makeup analysis | Planned |

## Current Pages
| Route | Status | Description |
|-------|--------|-------------|
| `/` | Live | Landing with key metrics |
| `/commanders` | Live | Commander rankings table |
| `/commanders/[id]` | Live | Detail with card frequencies, performance, players, and matchups |
| `/commanders/trends` | Live | Commander trendlines |
| `/trap-spice` | Live | Trap and spice cards |
| `/tournament-likelihood` | Live | Tournament finish probability tooling |
| `/regional-elo` | Live | Regional Elo leaderboards |
| `/regional-elo/player/[topdeckId]` | Live | Player regional Elo profile |
| `/midseason-invitational` | Live | Invitational event page |
| `/about` | Live | Project context and attribution |
| `/limitations` | Live | Caveats and methodology notes |

## Key Data Insights
- **52 tournaments** tracked
- **290 commanders** with stats
- **2,874 decks** analyzed
- **5,650 games** with seat data
- **Top trap card:** The One Ring (-1.64% win delta at 45% inclusion)

## Files Structure
```
src/
├── app/
│   ├── page.tsx                 # Landing page
│   ├── commanders/
│   │   ├── page.tsx             # Commander rankings
│   │   └── [id]/page.tsx        # Commander detail
│   │   └── trends/page.tsx      # Commander trendlines
│   ├── regional-elo/            # Regional Elo leaderboard + player pages
│   ├── tournament-likelihood/   # Tournament probability tools
│   └── trap-spice/page.tsx      # Trap & spice cards
├── components/ui/               # shadcn components
└── lib/
    ├── supabase.ts              # Supabase client + types
    └── utils.ts                 # shadcn utils
```

## Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=https://msjjihqbxtgjdtapywrj.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key-in-1password>
TOPDECK_API_KEY=<server-only>
```

## Design System
- **Background:** #0a0a0a (near black)
- **Cards:** #1a1a1a
- **Borders:** #2a2a2a
- **Primary accent:** #c9a227 (gold)
- **Secondary accent:** #8b5cf6 (purple)
- **Success:** #22c55e (green)
- **Warning:** #f59e0b (amber)
- **Error:** #ef4444 (red)
- **Text primary:** #fafafa
- **Text secondary:** #a1a1aa

## Pending Improvements
1. **Reviewability** - **[VITAL/KEEP]** Keep supported-surface docs and CI checks aligned. We need to ensure backend PRs do not fail on unrelated data dictionary gates.
2. **League Validation** - **[REJECTED/LOW]** Confirm TopDeck league payload support with authenticated samples. *Decision: Secondary to tournament data. Deferring indefinitely.*
3. **Observability** - **[REJECTED/LOW]** Add PostHog for supported surfaces only. *Decision: Deferring until core functional surfaces are fully stabilized. Not a priority right now.*

## Reference Sites
- **cedh.io** - Metagame statistics, deck analysis tools
- **topdeck.gg** - Tournament data source
- **scryfall.com** - Card images and search

## Session Notes
- "Unknown Commander" (1,209 entries) is real data where commander wasn't identified
- Color identity badges: W (amber), U (blue), B (purple), R (red), G (green)
- Anon key is safe for frontend (RLS enabled, read-only)
