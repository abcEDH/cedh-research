# QA Release Checklist

## Regional Elo
- Open one known player drilldown in a known region.
- Confirm `Current Rank`, `Counted Games`, and `Record` match the active row in `Regional Rankings`.
- Confirm the detailed game log is consistent with the same regional totals.
- Confirm the CI evidence artifact includes a real player/region proof row.
- Confirm production and preview resolve to the expected deployment when the change is intended to be live.

## Production sanity
- Verify the production domain points to the latest intended deployment.
- Spot-check one route that was updated in the PR on both preview and production.
- Confirm no user-facing analytics page presents conflicting totals and drilldowns.
