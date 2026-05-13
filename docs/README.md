# tedh.gg Documentation

Index of project documentation, methodology, and decision records.

## Core Identity
- **[Philosophy & Positioning](philosophy-and-positioning.md)**: Our core "Why," competitive differentiators, and interview strategy.
- **[Supported Surfaces](supported-surfaces.md)**: Inventory of live pages and features.

## Methodology
- **[cEDH Skill Rating (Elo)](methodology/cedh-skill-rating.md)**: Implementation of the 4-player Elo model.
- **[Meta Trends: Turbo Decks](methodology/meta-trends-2026.md)**: Empirical validation of Turbo deck performance in large events.
- **[Data Model](methodology/data-model.md)**: Supabase schema and ETL flow.
- **[Player Matchup Algorithm](player-matchup-algorithm.md)**: How we compute best/worst matchups.
- **[Tournament Prep Forecast](tournament-prep-update.md)**: Algorithm for predicting deck choice.

## Architectural Decisions
- **[Decision Records Index](decisions/README.md)**: MADR-formatted ADRs for load-bearing choices.

## Operations & QA
- **[QA Release Checklist](qa-release-checklist.md)**: Pre-deployment verification steps.
- **[PostHog Integration](POSTHOG_INTEGRATION.md)**: Analytics and error tracking setup.
- **[Production Domain Cutover](production-domain-cutover.md)**: Details on the `tedh.gg` migration.

## Historical Context (PR Summaries & Lessons)
- [Release Lessons - 2026-04-05](release-lessons-2026-04-05-regional-elo.md)
- [PR-124: Head-to-Head Records](pr-124-summary.md)
- [PR-109: TopDeck Elo Source](pr-109-summary.md)
- *(See `docs/` for full list of summaries)*

## Development Tools
- [Instant Spec Quickstart](instant-spec-quickstart.md)
- [Hand Input Templates](hand_input_templates.md)
