# Player Matchup Data Exports

This directory contains exported player matchup data for competitive analysis.

## Files

- `*_matchups.csv` - Detailed game-by-game records
- `*_summary.csv` - Aggregated win/loss statistics by opponent

## Columns

### Detailed Matchups (`*_matchups.csv`)
- `date` - Tournament start date (YYYY-MM-DD)
- `tournament` - Tournament name
- `player` - Player name
- `player_result` - Game result (WIN, LOSS, DRAW)
- `opponent` - Opponent name
- `opponent_topdeck_id` - Opponent's TopDeck ID

### Summary Statistics (`*_summary.csv`)
- `opponent` - Opponent name
- `opponent_topdeck_id` - Opponent's TopDeck ID
- `games` - Total games played
- `wins` - Number of wins
- `losses` - Number of losses
- `draws` - Number of draws
- `win_pct` - Win percentage

## Usage

Export data via the analytics page:
- Visit `/analytics/player-matchups`
- Enter a player name
- Select format (CSV or JSON) and data type (detailed or summary)
- Download the file

## Data Accuracy

Data is sourced from TopDeck tournament records and reflects all games from the tournaments in our database. Results are updated as new tournaments are ingested.

## Refresh Frequency

Export scripts can be run manually or scheduled as needed. Current exports reflect data as of the generation date.
