# cEDH Research - Development Context

## Project Overview
A Next.js 14 dashboard for competitive Magic: The Gathering (cEDH) tournament analytics, consuming data from a Supabase PostgreSQL backend with pre-computed materialized views.

**Live Site:** https://cedh-research.vercel.app
**Backend Repo:** ~/Documents/Repositories/personal/cedh-research

## Tech Stack
- **Framework:** Next.js 16 (App Router, TypeScript)
- **Styling:** Tailwind CSS + shadcn/ui components
- **Database:** Supabase (PostgreSQL with materialized views)
- **Deployment:** Vercel
- **Charts:** Recharts (planned)

## Database Views Available
| View | Description | Used In |
|------|-------------|---------|
| `commander_stats` | Commander performance summary | /commanders, / |
| `seat_position_stats` | Win rate by turn order | /turn-order |
| `card_frequencies_global` | Global card inclusion rates | /cards |
| `card_frequencies_by_commander` | Per-commander card rates | /commanders/[id] |
| `commander_card_report` | Cards with synergy scores | /commanders/[id] |
| `card_performance_by_commander` | Win rate correlation | Planned |
| `card_performance_global` | Global card win rates | Planned |
| `trap_cards_report` | Popular underperformers | /trap-spice |
| `spice_cards_report` | Rare overperformers | /trap-spice |
| `commander_head_to_head` | Matchup data | Planned (empty) |
| `round_win_rates` | Win rate by round | Planned |
| `commander_meta_share` | Meta representation | Planned |
| `commander_momentum` | Trending commanders | Planned |
| `commander_monthly_trends` | Time series | Planned |
| `player_seat_distribution` | Player seat patterns | Planned |
| `player_tournament_journey` | Player progression | Planned |
| `pod_composition` | Pod makeup analysis | Planned |
| `seat_by_tournament_size` | Seat advantage by size | Planned |

## Current Pages
| Route | Status | Description |
|-------|--------|-------------|
| `/` | Live | Landing with key metrics |
| `/commanders` | Live | Commander rankings table |
| `/commanders/[id]` | Live | Detail with card frequencies |
| `/cards` | Live | Global card frequency analysis |
| `/turn-order` | Live | Seat position fairness stats |
| `/trap-spice` | Live | Trap and spice cards |

## Key Data Insights
- **52 tournaments** tracked
- **290 commanders** with stats
- **2,874 decks** analyzed
- **5,650 games** with seat data
- **Turn order effect:** Seat 1 wins 23.6%, Seat 4 wins 13.2% (large effect)
- **Top trap card:** The One Ring (-1.64% win delta at 45% inclusion)

## Files Structure
```
src/
├── app/
│   ├── page.tsx                 # Landing page
│   ├── commanders/
│   │   ├── page.tsx             # Commander rankings
│   │   └── [id]/page.tsx        # Commander detail
│   ├── cards/page.tsx           # Card frequencies
│   ├── turn-order/page.tsx      # Turn order analysis
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
1. **Survival Analysis** - Round-by-round survival curves
2. **Statistical Significance** - Show confidence intervals on win rates
3. **Notable Players** - Track top performers per commander
4. **Commander Groupings** - Show which commanders use cards/trap-spice
5. **Tie Rates** - Add draw analysis to turn-order
6. **Card-Commander Links** - Bidirectional navigation

## Reference Sites
- **cedh.io** - Metagame statistics, deck analysis tools
- **topdeck.gg** - Tournament data source
- **scryfall.com** - Card images and search

## Session Notes
- "Unknown Commander" (1,209 entries) is real data where commander wasn't identified
- Color identity badges: W (amber), U (blue), B (purple), R (red), G (green)
- Anon key is safe for frontend (RLS enabled, read-only)
