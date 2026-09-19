import unittest
from pathlib import Path
from unittest.mock import Mock

from consolidate_names import regional_rows
from ingest import DataIngester, normalize_region_name, sanitize_commander_payload
from name_normalization import REGIONS, canonical_region_name


class NameNormalizationTests(unittest.TestCase):
    def test_every_region_full_name_and_code(self):
        for row in REGIONS:
            for alias in [row["name"], *row["aliases"]]:
                with self.subTest(alias=alias, country=row["country"]):
                    self.assertEqual(canonical_region_name(f" {alias.lower()} ", row["country"]), row["name"])

    def test_missing_country_only_resolves_unambiguous_aliases(self):
        self.assertEqual(canonical_region_name("TX"), "Texas")
        self.assertEqual(canonical_region_name("WA"), "WA")
        self.assertEqual(canonical_region_name("NT"), "NT")
        self.assertEqual(canonical_region_name("WA", "US"), "Washington")
        self.assertEqual(canonical_region_name("WA", "AU"), "Western Australia")
        self.assertEqual(canonical_region_name("BC", "United States"), "BC")

    def test_no_substring_matching(self):
        for name in ["Baja California", "West Virginia", "North Carolina", "New York Mills"]:
            self.assertEqual(canonical_region_name(name), name)
        self.assertEqual(normalize_region_name("CA", country="US"), "California")
        self.assertEqual(normalize_region_name("IN", country="US"), "Indiana")
        self.assertIsNone(canonical_region_name("undefined"))
        self.assertIsNone(canonical_region_name(" "))

    def test_commander_aliases_share_identity_before_batch_upsert(self):
        for alias in ["Kavaero, Mind-Bitten", "Kavaero, Mind−Bitten", "Superior Spider-Man"]:
            self.assertEqual(
                sanitize_commander_payload(alias, [alias]), ("Superior Spider-Man", ["Superior Spider-Man"])
            )
        client = Mock()
        client.upsert.return_value = [{"id": "canonical", "name": "Superior Spider-Man"}]
        result = DataIngester(Mock(), Mock(), write_client=client).batch_upsert_commanders(
            {
                "Kavaero, Mind-Bitten": ["Kavaero, Mind-Bitten"],
                "Superior Spider-Man": ["Superior Spider-Man"],
            }
        )
        self.assertEqual(result["Kavaero, Mind-Bitten"], result["Superior Spider-Man"])
        self.assertEqual(len(client.upsert.call_args.args[1]), 1)
        self.assertEqual(sanitize_commander_payload("Spider-Man 2099", ["Spider-Man 2099"])[0], "Spider-Man 2099")

    def test_region_migration_seed_matches_python_catalog(self):
        migration = (
            Path(__file__).resolve().parents[1]
            / "supabase/migrations/20260918170000_canonical_region_and_commander_names.sql"
        ).read_text()
        for row in REGIONS:
            for alias in [row["name"], *row["aliases"]]:
                values = ", ".join(
                    "'" + s.replace("'", "''") + "'" for s in [row["country"], alias.upper(), row["name"]]
                )
                self.assertIn("(" + values + ")", migration)

    def test_regional_rerank_preserves_global_ratings_and_counts(self):
        base = [
            {
                "player_id": p,
                "player_name": p,
                "region_type": "global",
                "region_key": "ALL",
                "country_key": None,
                "rating": rating,
                "topdeck_elo": td,
                "rank": i,
                "topdeck_elo_rank": i,
                "games_played": 15,
                "wins": 4,
                "draws": 2,
                "losses": 9,
            }
            for i, (p, rating, td) in enumerate([("a", 1600, 1400), ("b", 1500, 1700)], 1)
        ]
        activities = [
            {
                "player_id": p,
                "region_key": "TEXAS",
                "country_key": "UNITED STATES",
                "activity_score": 3,
                "is_primary_state": True,
            }
            for p in ["a", "b"]
        ]
        rows = regional_rows(base, activities)
        self.assertEqual(len(rows), 6)
        for old in base:
            new = next(r for r in rows if r["player_id"] == old["player_id"] and r["region_type"] == "global")
            for field in [
                "rating",
                "topdeck_elo",
                "rank",
                "topdeck_elo_rank",
                "games_played",
                "wins",
                "draws",
                "losses",
            ]:
                self.assertEqual(new[field], old[field])
        state = {r["player_id"]: r for r in rows if r["region_type"] == "state"}
        self.assertEqual(state["a"]["rank"], 1)
        self.assertEqual(state["b"]["topdeck_elo_rank"], 1)


class CommanderCatalogTests(unittest.TestCase):
    def test_verified_alias_families_and_partner_components(self):
        from ingest import normalize_commander_name

        examples = {
            "Egrix the Bile Bulwark": "Gwenom, Remorseless",
            "Seymour Guado": "Kinnan, Bonder Prodigy",
            "Chun-Li, Countless Kicks": "Zethi, Arcane Blademaster",
            "Rick, Steadfast Leader": "Greymond, Avacyn's Stalwart",
            "Cloud Strife": "Najeela, the Blade-Blossom",
        }
        for alias, canonical in examples.items():
            self.assertEqual(normalize_commander_name([alias]), canonical)
        self.assertEqual(
            normalize_commander_name(["Cecil Harvey", "Barnabas Tharmr"]),
            normalize_commander_name(["Tymna the Weaver", "Kraum, Ludevic's Opus"]),
        )
        self.assertEqual(normalize_commander_name(["Cloud, Midgar Mercenary"]), "Cloud, Midgar Mercenary")

    def test_catalog_has_provenance_and_matches_migration(self):
        import json

        from ingest import COMMANDER_NAME_ALIASES

        root = Path(__file__).resolve().parents[1]
        rows = json.loads((root / "data/commander_name_aliases.json").read_text())
        migration = (root / "supabase/migrations/20260918170000_canonical_region_and_commander_names.sql").read_text()
        for row in rows:
            self.assertTrue(row["oracle_id"])
            self.assertTrue(row["source"].startswith("https://scryfall.com/card/"))
            self.assertNotIn(row["canonical_name"], COMMANDER_NAME_ALIASES)
            values = ", ".join(
                "'" + row[k].replace("'", "''") + "'" for k in ["alias", "canonical_name", "oracle_id", "source"]
            )
            self.assertIn("(" + values + ")", migration)

    def test_generator_only_uses_exact_english_front_face_aliases(self):
        from generate_commander_aliases import aliases_from_cards

        base = {"name": "Real Commander // Back Face", "oracle_id": "id", "lang": "en", "scryfall_uri": "source"}
        card = {
            **base,
            "card_faces": [
                {"name": "Real Commander", "printed_name": "Alternate Commander"},
                {"name": "Back Face", "flavor_name": "Alternate Back"},
            ],
        }
        self.assertEqual(aliases_from_cards([card])[0]["alias"], "Alternate Commander")
        self.assertEqual(aliases_from_cards([card])[0]["canonical_name"], "Real Commander")
        self.assertEqual(aliases_from_cards([{**card, "lang": "ja"}]), [])
        with self.assertRaises(ValueError):
            aliases_from_cards([card, {**base, "name": "Different Commander", "flavor_name": "Alternate Commander"}])

    def test_double_faced_names_display_front_only(self):
        from ingest import clean_commander_card_name

        for name in ["Esika, God of the Tree // The Prismatic Bridge"]:
            self.assertEqual(clean_commander_card_name(name), "Esika, God of the Tree")
            self.assertEqual(
                sanitize_commander_payload(name, [name]), ("Esika, God of the Tree", ["Esika, God of the Tree"])
            )
        self.assertEqual(clean_commander_card_name("SP//dr, Piloted by Peni"), "SP//dr, Piloted by Peni")

    def test_database_uses_the_saved_partner_order(self):
        import json

        from ingest import PARTNER_ORDER_OVERRIDES, load_legal_commander_pair_order_map

        root = Path(__file__).resolve().parents[1]
        migration = (root / "supabase/migrations/20260918170000_canonical_region_and_commander_names.sql").read_text()
        seed = json.loads(migration.split("$partner_order$")[1])
        expected = load_legal_commander_pair_order_map().copy()
        for key, value in PARTNER_ORDER_OVERRIDES.items():
            expected.setdefault(key, value)
        self.assertEqual(seed, {" / ".join(key): list(value) for key, value in expected.items()})
