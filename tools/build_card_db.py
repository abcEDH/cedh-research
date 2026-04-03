#!/usr/bin/env python3
"""
Build a local SQLite database from Scryfall's bulk oracle-cards data.

Usage:
    python tools/build_card_db.py [--db PATH] [--force]

The database is stored at data/cards.db by default and provides zero-latency
card lookups for analysis scripts. Refresh monthly or when new sets release.
"""
import argparse
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path


DEFAULT_DB = Path('data/cards.db')
BULK_DATA_URL = 'https://api.scryfall.com/bulk-data'
SKIP_LAYOUTS = {'token', 'emblem', 'art_series', 'double_faced_token', 'vanguard', 'scheme', 'plane', 'phenomenon'}

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS cards (
    name            TEXT PRIMARY KEY,
    mana_cost       TEXT,
    type_line       TEXT,
    oracle_text     TEXT,
    power           TEXT,
    toughness       TEXT,
    color_identity  TEXT,
    keywords        TEXT,
    cmc             REAL,
    layout          TEXT
);
CREATE INDEX IF NOT EXISTS idx_name  ON cards(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_color ON cards(color_identity);
CREATE INDEX IF NOT EXISTS idx_cmc   ON cards(cmc);
'''


def get_bulk_url() -> str:
    req = urllib.request.Request(
        BULK_DATA_URL,
        headers={'User-Agent': 'CEDHResearch/1.0', 'Accept': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    for item in data['data']:
        if item['type'] == 'oracle_cards':
            return item['download_uri']
    raise RuntimeError('oracle_cards bulk data not found in Scryfall response')


def download_bulk(url: str) -> list:
    print(f'Downloading bulk data from Scryfall...')
    req = urllib.request.Request(url, headers={'User-Agent': 'CEDHResearch/1.0'})
    with urllib.request.urlopen(req) as resp:
        cards = json.load(resp)
    print(f'  Downloaded {len(cards):,} cards')
    return cards


def build_db(cards: list, db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for statement in CREATE_SQL.strip().split(';'):
        if statement.strip():
            c.execute(statement)

    inserted = 0
    for card in cards:
        if card.get('layout') in SKIP_LAYOUTS:
            continue
        c.execute(
            'INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?,?,?,?,?)',
            (
                card.get('name', ''),
                card.get('mana_cost', ''),
                card.get('type_line', ''),
                card.get('oracle_text', ''),
                card.get('power', ''),
                card.get('toughness', ''),
                ','.join(card.get('color_identity', [])),
                ','.join(card.get('keywords', [])),
                card.get('cmc', 0),
                card.get('layout', ''),
            )
        )
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


def lookup(name: str, db_path: Path) -> dict | None:
    """Single card lookup — usable by other scripts."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    row = c.execute(
        'SELECT name, mana_cost, type_line, oracle_text, power, toughness, color_identity, cmc '
        'FROM cards WHERE name = ?',
        (name,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'name': row[0], 'mana_cost': row[1], 'type_line': row[2],
        'oracle_text': row[3], 'power': row[4], 'toughness': row[5],
        'color_identity': row[6], 'cmc': row[7],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db', default=DEFAULT_DB, type=Path, help='Output SQLite database path')
    parser.add_argument('--force', action='store_true', help='Re-download even if db already exists')
    args = parser.parse_args()

    if args.db.exists() and not args.force:
        print(f'Database already exists at {args.db}. Use --force to rebuild.')
        sys.exit(0)

    url = get_bulk_url()
    cards = download_bulk(url)
    count = build_db(cards, args.db)
    print(f'Built {args.db} with {count:,} cards.')


if __name__ == '__main__':
    main()
