# 0015 - Canonical region and commander names

## Status
Accepted

## Context

Tournament locations contain both postal abbreviations and full names. Regional
queries uppercase these strings but do not combine them. Alternate commander
printings can likewise create distinct commander IDs, splitting profile history.

## Decision

- Store recognized regions using full names, with exact country-aware aliases in
  `region_name_aliases`. Existing analytical keys remain uppercase full names.
- Seed US states/territories, Canadian provinces/territories, Australian states/
  territories, and UK constituent countries from `region_aliases.json`.
- Preserve unknown and country-ambiguous names. Never use substring matching or
  assume an abbreviation belongs to the United States. Missing-country aliases
  resolve only when all matching catalog entries have the same canonical name.
- Resolve verified alternate card names through `commander_name_aliases` before
  persistence. Use Scryfall’s canonical name for the shared card identity. This covers English
  printed names (Universes Within/Omenpaths) and flavor-name treatments, including
  aliases within partner combinations. Kavaero, Mind-Bitten resolves to Superior
  Spider-Man; Egrix the Bile Bulwark resolves to Gwenom, Remorseless. Do not infer equivalence from similar names or similar rules text.
- Database triggers protect new writes. Ingestion uses matching normalization,
  and the frontend resolves old region query parameters using the same catalog.
- Merge commander references in base facts, then rebuild derived summaries;
  never sum already overlapping profile percentages or predictions.
- Use `consolidate_names.py` for the initial migration and derived refresh in one
  transaction, with audit and rollback rehearsal modes. It preserves Elo ratings,
  global leaderboard counters, tournament entries, and game events. Regional
  membership/ranks and commander predictions may change as duplicates combine.

## Consequences

Alias additions require a migration and matching catalog/ingestion updates.
Ambiguous source metadata still needs review. The initial rollout requires a
controlled write window for table locks and materialized-view refreshes. Deploy
ingestion changes with the migration; the old Python substring matcher can corrupt
values before the database sees them. Cached pages may retain old labels until
revalidation (player profile pages currently permit 24 hours).

Reviewed event exceptions are stored in `packages/backend/data/tournament_location_corrections.json`.
The 129 initial corrections resolve all short uppercase abbreviations left unresolved
by the initial audit: 66 Washington, three California, and 60 international records.
Each retains the original city, venue, state and country as evidence and guards.
One Sit&Game event has a date instead of an address; its saved city and the linked
official municipality directory establish Lower Saxony. These repairs do not treat
all missing countries, unknown full region names, or missing locations as audited.
The migration runner repairs these facts before rebuilding regional read models
in the same transaction. Ingestion reapplies reviewed repairs only when the event
ID, city, venue and source location still match, so a moved event is not overridden.

## Verification and rollout

```bash
PYTHONPATH=packages/backend/src python3 -m unittest discover -s packages/backend/tests -p 'test_name_normalization.py'
PYTHONPATH=packages/backend/src python3 packages/backend/src/consolidate_names.py
PYTHONPATH=packages/backend/src python3 packages/backend/src/consolidate_names.py --rehearse
PYTHONPATH=packages/backend/src python3 packages/backend/src/consolidate_names.py --apply
```

The runner records the migration in Supabase migration history. Run the runner
rather than applying this migration alone: source-name changes and derived
snapshots must become visible together. A repeated run rebuilds summaries without
reapplying the recorded migration. A rehearsal always rolls back, including its
migration-history entry. SQL errors, lock timeouts, or failed conservation checks
abort the transaction.

### Cross-Repo Impact

This repository only. Backend canonical facts and frontend region query parameters
share the catalog; no new external service is called during page requests.

## Sources

- [Data model](../methodology/data-model.md)
- `packages/backend/data/commander_name_aliases.json` records Scryfall oracle IDs
  and per-printing source links for each alias.
- [Wizards: Universes Within interchangeable names](https://magic.wizards.com/en/news/announcements/whats-new-on-the-list-for-wilds-of-eldraine)
- [Wizards: Through the Omenpaths](https://magic.wizards.com/en/news/announcements/through-the-omenpaths-and-digital-universes-beyond-updates)

Regenerate the commander catalog with `python3 packages/backend/src/generate_commander_aliases.py`.
Review changes and add a new migration before adopting a later catalog snapshot.
The generator follows every result page for English flavor-name printings, Secret
Lair printings, and every set whose name contains Through the Omenpaths. It refuses
conflicting aliases. Similar card text, unrelated cards depicting the same
character, and transform back faces are not evidence of shared identity.

## Partner order and double-faced cards

`commander_pair_display_order` is seeded from the existing `project_name` order in
`legal_commander_pairings.json` plus explicit fallback overrides. Alias resolution
happens before ordering. Both SQL and Python use that saved order, and strip each
component to its front face. Scryfall supplies card identity and legality, not the
project's community display order.

`partner_order_reviews.json` retains links to manually authored discussions,
primers, and deck titles. It records contrary examples when usage is mixed.
Confirmed reviews feed catalog generation; preserved orders are not automatically
claimed to be community-verified. New unreviewed pairs are marked
`alphabetical_pending_review`. This refresh retains all 3,135 remaining display
orders and removes five nonlegendary Battlebond partner-with combinations from
the legal commander catalog. It does not change their historical game facts.

The legality generator supports Scryfall's compressed JSONL bulk format as well
as the older JSON format. It checks commander eligibility in addition to format
legality, and requires the exact Time Lord/Doctor creature types for Doctor's
companion pairings.

### Coordinated release window

If deploying the frontend and ingestion from the same main-branch merge, pause
ingestion dispatch first and ensure no ingestion job is still running. Apply the
validated database cleanup, merge/deploy the compatible code, then restore
ingestion dispatch. The frontend cache keys change with this release so the new
deployment reads the corrected regional summaries. Do not resume old ingestion
between database commit and code deployment.

### Post-release location review

The September 19 ingestion audit identified one additional event, `mtm-series-iv`,
with `SL` and no country. Its TopDeck event page identifies Dillingen/Saar, Germany;
the official municipality directory confirms Saarland. The reviewed correction
catalog now contains 130 events. This is an event-specific correction, not a
global interpretation of `SL` without country context. Source links and the
original city, missing venue, state, and country are retained in the catalog.
