# Player Matchup Data Exports

This directory documents the player matchup data exposed by the JSON export API for
competitive analysis.

## Files

- `*_matchups.json` - Detailed game-by-game records
- `*_summary.json` - Aggregated win/loss statistics by opponent

## Columns

### Detailed Matchups (`*_matchups.json`)
- `date` - Tournament start date (YYYY-MM-DD)
- `tournament` - Tournament name
- `player` - Player name
- `player_result` - Game result (WIN, LOSS, DRAW)
- `opponent` - Opponent name
- `opponent_topdeck_id` - Opponent's TopDeck ID
- `elo_tier` - Eligibility tier used for the export (`ranking`, `local`, or `all`)
- `tier_label` - Human-readable eligibility label
- `tournament_player_count` - Number of players in the tournament, when available

### Summary Statistics (`*_summary.json`)
- `opponent` - Opponent name
- `opponent_topdeck_id` - Opponent's TopDeck ID
- `games` - Total games played
- `wins` - Number of wins
- `losses` - Number of losses
- `draws` - Number of draws
- `win_pct` - Win percentage
- `elo_tier` - Eligibility tier used for the export
- `tier_label` - Human-readable eligibility label

## Usage

Export JSON data via the analytics page:
- Visit `/analytics/player-matchups`
- Enter a player name
- Select detailed or summary data
- Download the file

The API also accepts `format=json` and `type=detailed|summary`; CSV requests are
rejected because JSON is the supported export format.

## Data Accuracy

Data is sourced from TopDeck tournament records and reflects all games from the tournaments in our database. Results are updated as new tournaments are ingested.

## Refresh Frequency

Export scripts can be run manually or scheduled as needed. Current exports reflect data as of the generation date.
