# tedh.gg

tedh.gg is a cEDH site for players who want a fast read on commanders, tournaments, and trends with a clean, Kamigawa: Neon Dynasty-inspired interface.

## What you can do

- Explore commander rankings and performance deltas
- Compare conversion rates (Top 16 / Top Cut)
- Analyze seat position advantage
- Track survival trends across tournament rounds

## Local development

```bash
npm run dev -- --port 4322 --hostname 127.0.0.1
```

Open `http://127.0.0.1:4322/` and jump straight into the dashboard.

## Tech stack

- Next.js (App Router)
- Supabase for data access
- Tailwind CSS v4
- Recharts for visualizations

## Roadmap ideas

- Add card art thumbnails for top commanders
- Mini archetype badges (Turbo, Midrange, Stax, Control)
- Event map view for regional meta heat

## Repository

GitHub: https://github.com/victoremnm/cedh-research

## Live tournament scouting

`/tournament-likelihood` reads standings and rounds from TopDeck on every page
refresh. Visible tabs refresh every 60 seconds, with a manual refresh button.
Historical commander forecasts remain cached for 15 minutes, keyed by attendee
IDs, event start time, and whether the event has started.

The web server needs `TOPDECK_API_KEY` in its **server runtime environment**
(Vercel Production and Preview, followed by a redeploy). Never prefix it with
`NEXT_PUBLIC_` or put it in the frontend `.env.local`; supply it through the
server process environment for local development. Without the key, public
attendee scouting still works, but live standings are explicitly unavailable.
API errors are displayed and retried on refresh rather than replaced with fake
zero results. Submitted decks can remain private during the event; in that case
current standings are paired with clearly labeled historical deck forecasts.

Upstream contract: https://topdeck.gg/docs/tournaments-v2
