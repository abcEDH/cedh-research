import os
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import requests as requests_module
except ModuleNotFoundError:
    requests_module = types.ModuleType("requests")
    requests_module.get = Mock()
    requests_module.post = Mock()
    requests_module.patch = Mock()
    requests_module.exceptions = types.SimpleNamespace(
        ConnectionError=ConnectionError,
        Timeout=TimeoutError,
        ReadTimeout=TimeoutError,
        JSONDecodeError=ValueError,
        HTTPError=RuntimeError,
        RequestException=Exception,
    )
    sys.modules["requests"] = requests_module

dateutil_module = types.ModuleType("dateutil")
dateutil_parser_module = types.ModuleType("dateutil.parser")
dateutil_parser_module.parse = lambda value: value
dateutil_module.parser = dateutil_parser_module
sys.modules.setdefault("dateutil", dateutil_module)
sys.modules.setdefault("dateutil.parser", dateutil_parser_module)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingest import (  # noqa: E402
    INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE,
    DataIngester,
    claim_ingestion_job,
    clean_commander_card_name,
    complete_ingestion_job,
    extract_standing_rates,
    fail_ingestion_job,
    fetch_existing_partner_order_map,
    load_commander_oracle_aliases,
    main,
    normalize_commander_name,
    normalize_partner_order,
    resolve_record_fields,
    sanitize_commander_payload,
)


def _make_fluent_client() -> Mock:
    """Build a Mock supabase-py Client whose `.table(name).select(...)` and
    `.table(name).update(...)` chains (any `.eq()`/`.in_()`/`.order()`/etc in
    any order) resolve to a shared `.execute().data`, mirroring the fluent
    builder ingest.py now uses. `.upsert(...)` is left for callers to
    configure per-test since its return value usually depends on the payload.
    """
    client = Mock()

    select_chain = Mock()
    for method in ("eq", "neq", "gte", "lte", "gt", "lt", "ilike", "in_", "order", "limit", "offset"):
        getattr(select_chain, method).return_value = select_chain
    select_chain.not_ = Mock()
    select_chain.not_.is_.return_value = select_chain
    client.table.return_value.select.return_value = select_chain

    update_chain = Mock()
    for method in ("eq", "in_"):
        getattr(update_chain, method).return_value = update_chain
    client.table.return_value.update.return_value = update_chain

    return client


class ResolveRecordFieldsTests(unittest.TestCase):
    def test_uses_explicit_wins_losses_draws_when_present(self) -> None:
        info = {"wins": 4, "losses": 1, "draws": 0, "points": 20}

        fields = resolve_record_fields(info)

        self.assertEqual(fields, {"wins": 4, "losses": 1, "draws": 0})

    def test_does_not_derive_wins_or_draws_from_points_when_missing(self) -> None:
        # Regression guard: merlion-anniversary-cedh reported points=1866 with no
        # explicit wins/losses/draws. The old fallback (points // 5, points % 5)
        # fabricated a 373-0-1 record, which is impossible for a 5-round event.
        # Point-scoring formulas vary per tournament/organizer and are not a
        # reliable stand-in for an explicit record.
        info = {"wins": None, "losses": None, "draws": None, "points": 1866}

        fields = resolve_record_fields(info)

        self.assertEqual(fields, {})

    def test_uses_only_the_fields_that_are_explicitly_present(self) -> None:
        info = {"wins": 3, "losses": None, "draws": None, "points": 15}

        fields = resolve_record_fields(info)

        self.assertEqual(fields, {"wins": 3})


class ExtractStandingRatesTests(unittest.TestCase):
    def test_uses_primary_and_opponent_fallbacks_independently(self) -> None:
        standing = {
            "successRate": 0.72,
            "opponentWinRate": 0.41,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.72)
        self.assertEqual(opponent_win_rate, 0.41)

    def test_accepts_percent_values_for_both_fields(self) -> None:
        standing = {
            "winRate": 71,
            "opponentSuccessRate": 48,
        }

        win_rate, opponent_win_rate = extract_standing_rates(standing)

        self.assertEqual(win_rate, 0.71)
        self.assertEqual(opponent_win_rate, 0.48)


class CommanderNormalizationTests(unittest.TestCase):
    def test_clean_commander_card_name_maps_stranger_things_to_in_universe(self) -> None:
        self.assertEqual(clean_commander_card_name("Lucas, the Sharpshooter"), "Bjorna, Nightfall Alchemist")

    def test_clean_commander_card_name_unescapes_quotes(self) -> None:
        self.assertEqual(clean_commander_card_name("K\\'rrik, Son of Yawgmoth"), "K'rrik, Son of Yawgmoth")

    def test_clean_commander_card_name_normalizes_curly_apostrophe(self) -> None:
        # TopDeck/Moxfield sources are inconsistent about curly (U+2019) vs
        # straight apostrophes for the same card, which previously produced
        # two different canonical names for one commander.
        self.assertEqual(
            clean_commander_card_name("Kraum, Ludevic’s Opus"),
            clean_commander_card_name("Kraum, Ludevic's Opus"),
        )

    def test_clean_commander_card_name_normalizes_curly_double_quote(self) -> None:
        self.assertEqual(
            clean_commander_card_name("“Commander” Name"),
            '"Commander" Name',
        )

    def test_normalize_partner_order_matches_regardless_of_apostrophe_style(self) -> None:
        # A partner pair ingested in both name orders, where one order also
        # uses a curly apostrophe, must still collapse onto the same
        # canonical order (issue #260).
        straight_order = normalize_partner_order(["Kraum, Ludevic's Opus", "Tymna the Weaver"])
        curly_order = normalize_partner_order(["Tymna the Weaver", "Kraum, Ludevic’s Opus"])
        self.assertEqual(straight_order, curly_order)

    def test_clean_commander_card_name_strips_double_faced_backside(self) -> None:
        self.assertEqual(
            clean_commander_card_name("Etali, Primal Conqueror // Etali, Primal Sickness"),
            "Etali, Primal Conqueror",
        )

    def test_clean_commander_card_name_falls_back_to_generated_oracle_alias_map(self) -> None:
        # A newly-released Universes Beyond alternate-name printing that hasn't
        # been hand-added to COMMANDER_NAME_ALIASES yet should still resolve
        # via the generated commander_oracle_aliases.json artifact, keyed off
        # the underlying Scryfall oracle_id (see generate_commander_oracle_aliases.py).
        load_commander_oracle_aliases.cache_clear()
        try:
            with patch(
                "ingest.load_commander_oracle_aliases",
                return_value={"Totally Radical Skater": "Nadier, Agent of the Duskenel"},
            ):
                self.assertEqual(
                    clean_commander_card_name("Totally Radical Skater"),
                    "Nadier, Agent of the Duskenel",
                )
        finally:
            load_commander_oracle_aliases.cache_clear()

    def test_hardcoded_alias_takes_precedence_over_generated_alias_map(self) -> None:
        load_commander_oracle_aliases.cache_clear()
        try:
            with patch(
                "ingest.load_commander_oracle_aliases",
                return_value={"Lucas, the Sharpshooter": "Some Other Card"},
            ):
                self.assertEqual(
                    clean_commander_card_name("Lucas, the Sharpshooter"),
                    "Bjorna, Nightfall Alchemist",
                )
        finally:
            load_commander_oracle_aliases.cache_clear()

    def test_load_commander_oracle_aliases_reads_generated_artifact(self) -> None:
        load_commander_oracle_aliases.cache_clear()
        try:
            aliases = load_commander_oracle_aliases()
        finally:
            load_commander_oracle_aliases.cache_clear()
        self.assertIsInstance(aliases, dict)
        self.assertEqual(aliases.get("Chief Jim Hopper"), "Sophina, Spearsage Deserter")

    def test_normalize_commander_name_strips_back_faces_from_partner_pair(self) -> None:
        self.assertEqual(
            normalize_commander_name(
                [
                    "Etali, Primal Conqueror // Etali, Primal Sickness",
                    "Vivi Ornitier",
                ]
            ),
            "Etali, Primal Conqueror / Vivi Ornitier",
        )

    def test_sanitize_commander_payload_canonicalizes_name_and_components(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Kraum, Ludevic\\'s Opus / Tymna the Weaver",
                ["Kraum, Ludevic\\'s Opus", "Tymna the Weaver"],
            ),
            (
                "Tymna the Weaver / Kraum, Ludevic's Opus",
                ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
            ),
        )

    def test_sanitize_commander_payload_maps_stranger_things_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Lucas, the Sharpshooter / Will the Wise",
                ["Lucas, the Sharpshooter", "Will the Wise"],
            ),
            (
                "Bjorna, Nightfall Alchemist / Wernog, Rider's Chaplain",
                ["Bjorna, Nightfall Alchemist", "Wernog, Rider's Chaplain"],
            ),
        )

    def test_sanitize_commander_payload_rejects_illegal_pair(self) -> None:
        self.assertEqual(
            sanitize_commander_payload(
                "Etali, Primal Conqueror / Kinnan, Bonder Prodigy",
                ["Etali, Primal Conqueror", "Kinnan, Bonder Prodigy"],
            ),
            ("Unknown Commander", ["Unknown Commander"]),
        )

    def test_normalize_commander_name_uses_canonical_legal_pair_order(self) -> None:
        self.assertEqual(
            normalize_commander_name(["Haldan, Avid Arcanist", "Pako, Arcane Retriever"]),
            "Pako, Arcane Retriever / Haldan, Avid Arcanist",
        )

    def test_normalize_commander_name_is_order_independent_for_unregistered_pair(self) -> None:
        # A pair with no legal_commander_pairings.json entry and no
        # PARTNER_ORDER_OVERRIDES entry falls back to an alphabetical sort, which
        # must be reached regardless of which order the decklist listed the two
        # commanders in.
        self.assertEqual(
            normalize_commander_name(["Zndrsplt, Eye of Wisdom", "Okaun, Eye of Chaos"]),
            normalize_commander_name(["Okaun, Eye of Chaos", "Zndrsplt, Eye of Wisdom"]),
        )


class PartnerOrderReconciliationTests(unittest.TestCase):
    """Issue #260: partner pairs ingested in either name order must resolve to
    one canonical commander row instead of splitting into "A, B" vs "B, A".
    """

    def test_fetch_existing_partner_order_map_builds_sorted_pair_lookup(self) -> None:
        client = _make_fluent_client()
        client.table.return_value.select.return_value.execute.return_value.data = [
            {
                "commander_names": ["Tymna the Weaver", "Kraum, Ludevic's Opus"],
                "created_at": "2026-01-01T00:00:00Z",
            },
            {"commander_names": ["Some Single Commander"], "created_at": "2026-01-02T00:00:00Z"},
            {"commander_names": None, "created_at": "2026-01-03T00:00:00Z"},
        ]

        order_map = fetch_existing_partner_order_map(client)

        self.assertEqual(
            order_map[tuple(sorted(["Tymna the Weaver", "Kraum, Ludevic's Opus"]))],
            ("Tymna the Weaver", "Kraum, Ludevic's Opus"),
        )
        self.assertEqual(len(order_map), 1)

    def test_reconcile_partner_order_prefers_existing_db_row(self) -> None:
        supabase = _make_fluent_client()
        supabase.table.return_value.select.return_value.execute.return_value.data = [
            {
                "commander_names": ["Zzzephyr, Test Commander", "Aaardvark, Test Partner"],
                "created_at": "2025-01-01T00:00:00Z",
            }
        ]
        ingester = DataIngester(Mock(), supabase)

        reconciled_name, reconciled_names = ingester._reconcile_partner_order(
            "Aaardvark, Test Partner / Zzzephyr, Test Commander",
            ["Aaardvark, Test Partner", "Zzzephyr, Test Commander"],
        )

        self.assertEqual(reconciled_name, "Zzzephyr, Test Commander / Aaardvark, Test Partner")
        self.assertEqual(reconciled_names, ["Zzzephyr, Test Commander", "Aaardvark, Test Partner"])
        # The lookup is cached: a second call must not re-query Supabase.
        ingester._reconcile_partner_order("x", ["Aaardvark, Test Partner", "Zzzephyr, Test Commander"])
        supabase.table.return_value.select.assert_called_once()

    @patch("ingest.load_legal_commander_pair_order_map", return_value={})
    @patch(
        "ingest.load_legal_commander_pair_names",
        return_value={"Aaardvark, Test Partner / Zzzephyr, Test Commander"},
    )
    def test_batch_upsert_commanders_merges_both_orders_into_existing_row(
        self, _mock_legal_names: Mock, _mock_legal_order: Mock
    ) -> None:
        """Simulates a pair whose DB row order (e.g. from a legacy insert, or a
        prior ``sweep_partner_commander_order.py`` rename) disagrees with the
        alphabetical fallback ``normalize_partner_order()`` would compute fresh.
        Ingesting that pair from two independent tournaments -- one where the
        decklist lists the commanders alphabetically, one where it lists them in
        the DB's established order -- must both resolve to the *same* existing
        commander row rather than one of them creating a duplicate.
        """
        existing_order = ("Zzzephyr, Test Commander", "Aaardvark, Test Partner")
        pair_key = tuple(sorted(existing_order))  # the alphabetical fallback order

        supabase = _make_fluent_client()
        supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"commander_names": list(existing_order), "created_at": "2025-01-01T00:00:00Z"}
        ]

        def fake_upsert(data, on_conflict=None):
            result = [{"name": row["name"], "id": "commander-1"} for row in data]
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))

        supabase.table.return_value.upsert.side_effect = fake_upsert

        # Tournament A's decklist lists the commanders alphabetically.
        ingester_a = DataIngester(Mock(), supabase)
        commander_name_a = normalize_commander_name(list(pair_key))
        id_map_a = ingester_a.batch_upsert_commanders({commander_name_a: list(pair_key)})

        # Tournament B's decklist lists the same two commanders in the other order.
        ingester_b = DataIngester(Mock(), supabase)
        commander_name_b = normalize_commander_name(list(reversed(pair_key)))
        id_map_b = ingester_b.batch_upsert_commanders({commander_name_b: list(reversed(pair_key))})

        # Both must resolve to the single existing commander row.
        self.assertEqual(id_map_a[commander_name_a], "commander-1")
        self.assertEqual(id_map_b[commander_name_b], "commander-1")

        for call in supabase.table.return_value.upsert.call_args_list:
            data = call.args[0]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], " / ".join(existing_order))
            self.assertEqual(data[0]["commander_names"], list(existing_order))

    @patch("ingest.load_legal_commander_pair_order_map", return_value={})
    @patch(
        "ingest.load_legal_commander_pair_names",
        return_value={"Aaardvark, Test Partner / Zzzephyr, Test Commander"},
    )
    def test_batch_upsert_commanders_dedupes_two_keys_reconciling_to_same_row(
        self, _mock_legal_names: Mock, _mock_legal_order: Mock
    ) -> None:
        """Reconciliation can make two distinct original keys resolve to the
        same existing row (the explicit reason the return map is keyed by the
        pre-reconciliation name). The upsert payload must contain a single
        deduped row (PostgREST can't target the same ``on_conflict`` row twice
        in one call), and both original keys must map to the one returned id.
        """
        existing_order = ("Zzzephyr, Test Commander", "Aaardvark, Test Partner")
        pair_key = tuple(sorted(existing_order))  # alphabetical fallback order
        key_alpha = " / ".join(pair_key)  # "Aaardvark, Test Partner / Zzzephyr, Test Commander"
        key_reverse = " / ".join(reversed(pair_key))  # "Zzzephyr, Test Commander / Aaardvark, Test Partner"

        supabase = _make_fluent_client()
        supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"commander_names": list(existing_order), "created_at": "2025-01-01T00:00:00Z"}
        ]

        upsert_calls: list[dict] = []

        def fake_upsert(data, on_conflict=None):
            upsert_calls.append({"data": data, "on_conflict": on_conflict})
            result = [{"name": row["name"], "id": "commander-1"} for row in data]
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))

        supabase.table.return_value.upsert.side_effect = fake_upsert

        ingester = DataIngester(Mock(), supabase)
        id_map = ingester.batch_upsert_commanders({key_alpha: list(pair_key), key_reverse: list(reversed(pair_key))})

        # Exactly one upsert call, with a single deduped row in the DB's
        # established order.
        self.assertEqual(len(upsert_calls), 1)
        self.assertEqual(len(upsert_calls[0]["data"]), 1)
        self.assertEqual(upsert_calls[0]["data"][0]["name"], " / ".join(existing_order))
        self.assertEqual(upsert_calls[0]["data"][0]["commander_names"], list(existing_order))

        # Both original keys resolve to the one existing row's id.
        self.assertEqual(id_map[key_alpha], "commander-1")
        self.assertEqual(id_map[key_reverse], "commander-1")
        self.assertEqual(len(id_map), 2)

    @patch("ingest.load_legal_commander_pair_order_map", return_value={})
    @patch(
        "ingest.load_legal_commander_pair_names",
        return_value={"Aaardvark, Test Partner / Zzzephyr, Test Commander"},
    )
    def test_get_or_create_commander_reconciles_to_existing_db_order(
        self, _mock_legal_names: Mock, _mock_legal_order: Mock
    ) -> None:
        """The legacy single-row write path (``get_or_create_commander``) was
        modified to call ``_reconcile_partner_order`` just like the batch path.
        Feeding it a pair whose freshly-computed name (alphabetical) disagrees
        with the DB's established order must reconcile to the DB's order before
        the lookup/upsert, so it doesn't create a duplicate row under the
        alphabetical name.
        """
        existing_order = ("Zzzephyr, Test Commander", "Aaardvark, Test Partner")
        pair_key = tuple(sorted(existing_order))  # alphabetical fallback
        alpha_name = " / ".join(pair_key)

        supabase = _make_fluent_client()
        # ``fetch_existing_partner_order_map`` reads via ``select`` with the
        # ``commander_names,created_at`` projection; the legacy path then does
        # its own ``select`` lookup by the reconciled name. The first call
        # builds the order map; the second must return the existing row for the
        # reconciled name so the legacy path finds it instead of creating a
        # duplicate.
        supabase.table.return_value.select.return_value.execute.side_effect = [
            SimpleNamespace(
                data=[{"commander_names": list(existing_order), "created_at": "2025-01-01T00:00:00Z"}]
            ),  # order map
            SimpleNamespace(data=[{"id": "commander-1", "name": " / ".join(existing_order)}]),  # legacy lookup hit
        ]

        ingester = DataIngester(Mock(), supabase)
        result_id = ingester.get_or_create_commander(alpha_name, list(pair_key))

        self.assertEqual(result_id, "commander-1")
        # The legacy path must have looked up by the *reconciled* name, not the
        # alphabetical one -- otherwise it would have missed the row and
        # inserted a duplicate.
        legacy_lookup_call = supabase.table.return_value.select.return_value.eq.call_args_list[-1]
        self.assertEqual(legacy_lookup_call.args, ("name", " / ".join(existing_order)))
        # And no upsert/create should have been needed.
        supabase.table.return_value.upsert.assert_not_called()

    @patch("ingest.load_legal_commander_pair_order_map", return_value={})
    @patch(
        "ingest.load_legal_commander_pair_names",
        return_value={"Aaardvark, Test Partner / Zzzephyr, Test Commander"},
    )
    def test_batch_upsert_commanders_drops_keys_missing_from_upsert_result(
        self, _mock_legal_names: Mock, _mock_legal_order: Mock
    ) -> None:
        """The return-map comprehension guards ``if canonical_name in
        name_to_id``. If the upsert returns a subset of rows (e.g. a row that
        was filtered server-side), the corresponding original keys must be
        silently dropped from the returned map rather than raising KeyError.
        """
        existing_order = ("Zzzephyr, Test Commander", "Aaardvark, Test Partner")
        pair_key = tuple(sorted(existing_order))
        single_commander_name = "Solo, Test Commander"

        supabase = _make_fluent_client()
        supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"commander_names": list(existing_order), "created_at": "2025-01-01T00:00:00Z"}
        ]

        def fake_upsert(data, on_conflict=None):
            # Only echo back the single-commander row; drop the partner row.
            result = [{"name": row["name"], "id": "solo-id"} for row in data if row["name"] == single_commander_name]
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=result))

        supabase.table.return_value.upsert.side_effect = fake_upsert

        ingester = DataIngester(Mock(), supabase)
        id_map = ingester.batch_upsert_commanders(
            {
                " / ".join(pair_key): list(pair_key),
                single_commander_name: [single_commander_name],
            }
        )

        # The partner pair (absent from the upsert result) is dropped; only the
        # single commander survives in the returned map.
        self.assertEqual(id_map, {single_commander_name: "solo-id"})

    @patch("ingest.load_legal_commander_pair_order_map", return_value={})
    @patch(
        "ingest.load_legal_commander_pair_names",
        return_value={"Aaardvark, Test Partner / Zzzephyr, Test Commander"},
    )
    def test_commander_cache_keyed_by_pre_reconciliation_name(
        self, _mock_legal_names: Mock, _mock_legal_order: Mock
    ) -> None:
        """``ingest_tournament`` does ``self.commander_cache.update(id_map)``
        with the original-key-keyed map, and the legacy path later looks up by
        ``name``. After a reconciled upsert, the cache is keyed by the
        pre-reconciliation (alphabetical) name; a subsequent legacy-path lookup
        by the *reconciled* name misses the cache and re-queries the DB. This
        documents that contract: the cache is intentionally keyed by the name
        ``process_tournament`` computed, not by the reconciled name that was
        actually persisted.
        """
        existing_order = ("Zzzephyr, Test Commander", "Aaardvark, Test Partner")
        pair_key = tuple(sorted(existing_order))
        alpha_name = " / ".join(pair_key)
        reconciled_name = " / ".join(existing_order)

        supabase = _make_fluent_client()
        supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"commander_names": list(existing_order), "created_at": "2025-01-01T00:00:00Z"}
        ]
        supabase.table.return_value.upsert.side_effect = lambda data, on_conflict=None: SimpleNamespace(
            execute=lambda: SimpleNamespace(data=[{"name": row["name"], "id": "commander-1"} for row in data])
        )

        ingester = DataIngester(Mock(), supabase)
        id_map = ingester.batch_upsert_commanders({alpha_name: list(pair_key)})
        ingester.commander_cache.update(id_map)

        # The cache is keyed by the pre-reconciliation name (what the caller
        # computed), NOT by the reconciled name that was persisted.
        self.assertIn(alpha_name, ingester.commander_cache)
        self.assertEqual(ingester.commander_cache[alpha_name], "commander-1")
        # The reconciled name is NOT in the cache -- a legacy-path lookup by it
        # would miss and re-query the DB. This is intentional: the batch path
        # and the legacy path compute their own names upstream and look up by
        # those, so the cache must be keyed to match what they'll ask for.
        self.assertNotIn(reconciled_name, ingester.commander_cache)

    def test_reconcile_partner_order_cache_hit_through_two_element_branch(self) -> None:
        """The cache-hit path through the 2-element reconciliation branch: a
        second 2-element call must reuse the cached order map (no new
        ``select``) and reconcile against the established DB order.
        """
        existing_order = ("Zzzephyr, Test Commander", "Aaardvark, Test Partner")
        pair_key = tuple(sorted(existing_order))

        supabase = _make_fluent_client()
        supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"commander_names": list(existing_order), "created_at": "2025-01-01T00:00:00Z"}
        ]
        ingester = DataIngester(Mock(), supabase)

        # First call populates the cache and reconciles to the DB order.
        name1, names1 = ingester._reconcile_partner_order(
            " / ".join(pair_key),
            list(pair_key),
        )
        self.assertEqual(name1, " / ".join(existing_order))
        self.assertEqual(names1, list(existing_order))

        # Second 2-element call: must reuse the cache (no new select) and still
        # reconcile. Passing the DB's own order so the "no change" sub-branch
        # is the one exercised.
        name2, names2 = ingester._reconcile_partner_order(
            " / ".join(existing_order),
            list(existing_order),
        )
        self.assertEqual(name2, " / ".join(existing_order))
        self.assertEqual(names2, list(existing_order))

        # Exactly one select call across both reconciliations.
        supabase.table.return_value.select.assert_called_once()


class IngestionJobLifecycleTests(unittest.TestCase):
    def test_claim_ingestion_job_sends_update(self) -> None:
        client = _make_fluent_client()
        client.table.return_value.update.return_value.execute.return_value.data = [{"id": "job-1"}]
        result = claim_ingestion_job(client, "job-1", github_run_id=99)
        self.assertTrue(result)
        client.table.assert_any_call("ingestion_jobs")
        update_call = client.table.return_value.update.call_args
        self.assertEqual(update_call.args[0]["status"], "running")
        self.assertEqual(update_call.args[0]["github_run_id"], 99)
        client.table.return_value.update.return_value.eq.assert_called_once_with("id", "job-1")
        client.table.return_value.update.return_value.in_.assert_called_once_with("status", ["pending", "dispatched"])

    def test_claim_ingestion_job_returns_false_on_empty(self) -> None:
        client = _make_fluent_client()
        client.table.return_value.update.return_value.execute.return_value.data = []
        result = claim_ingestion_job(client, "job-1", github_run_id=0)
        self.assertFalse(result)

    def test_claim_ingestion_job_raises_on_operational_error(self) -> None:
        client = _make_fluent_client()
        client.table.return_value.update.return_value.execute.side_effect = ConnectionError("Supabase unreachable")
        with self.assertRaises(ConnectionError):
            claim_ingestion_job(client, "job-1", github_run_id=0)

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.update_ingestion_heartbeat")
    @patch("ingest.claim_ingestion_job")
    @patch("ingest.DataIngester")
    @patch("ingest.get_supabase_client")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_main_exits_with_distinct_code_when_job_already_claimed(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_claim_ingestion_job: Mock,
        mock_update_ingestion_heartbeat: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        mock_claim_ingestion_job.return_value = False

        with patch.object(sys, "argv", ["ingest.py", "--job-id", "job-1"]):
            with self.assertRaises(SystemExit) as exc:
                main()

        self.assertEqual(exc.exception.code, INGESTION_JOB_ALREADY_CLAIMED_EXIT_CODE)
        mock_update_ingestion_heartbeat.assert_not_called()
        mock_run_ingestion.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "TOPDECK_API_KEY": "topdeck-key",
            "SUPABASE_SERVICE_KEY": "supabase-key",
            "SUPABASE_URL": "https://test.supabase.co",
        },
        clear=False,
    )
    @patch("ingest._run_ingestion")
    @patch("ingest.update_ingestion_heartbeat")
    @patch("ingest.claim_ingestion_job")
    @patch("ingest.DataIngester")
    @patch("ingest.get_supabase_client")
    @patch("ingest.TopDeckClient")
    @patch("ingest.load_local_env")
    def test_main_exits_when_claim_ingestion_job_errors(
        self,
        mock_load_local_env: Mock,
        mock_topdeck_client: Mock,
        mock_supabase_client: Mock,
        mock_data_ingester: Mock,
        mock_claim_ingestion_job: Mock,
        mock_update_ingestion_heartbeat: Mock,
        mock_run_ingestion: Mock,
    ) -> None:
        mock_claim_ingestion_job.side_effect = ConnectionError("Supabase unreachable")

        with patch.object(sys, "argv", ["ingest.py", "--job-id", "job-1"]):
            with self.assertRaises(SystemExit) as exc:
                main()

        self.assertEqual(exc.exception.code, 1)
        mock_claim_ingestion_job.assert_called_once()
        mock_update_ingestion_heartbeat.assert_not_called()
        mock_run_ingestion.assert_not_called()

    def test_fail_ingestion_job_truncates_error(self) -> None:
        client = _make_fluent_client()
        fail_ingestion_job(client, "job-1", "x" * 3000)
        call_args = client.table.return_value.update.call_args
        self.assertLessEqual(len(call_args.args[0]["error_text"]), 2000)

    def test_complete_ingestion_job_sets_completed_status(self) -> None:
        client = _make_fluent_client()
        complete_ingestion_job(client, "job-1", {"duration_seconds": 42.5})
        call_args = client.table.return_value.update.call_args
        self.assertEqual(call_args.args[0]["status"], "completed")
        self.assertEqual(call_args.args[0]["duration_seconds"], 42.5)


class ProcessTournamentFutureStartDateTests(unittest.TestCase):
    """``process_tournament`` must refuse to ingest events whose start_date is
    implausibly far in the future (e.g. TopDeck test/practice events created
    with a placeholder date years out) -- see the "test-event-for-dan-and-noam"
    incident where such an event polluted production stats.

    Note: the module-level ``dateutil.parser.parse`` stub used across this test
    file is an identity function, so these tests use numeric (epoch) startDate
    values -- the only path that produces a real ``datetime`` via
    ``datetime.fromtimestamp`` under that stub.
    """

    def test_skips_tournament_with_far_future_start_date(self) -> None:
        supabase = Mock()
        topdeck = Mock()
        ingester = DataIngester(topdeck, supabase)

        far_future_epoch = (datetime.now() + timedelta(days=400)).timestamp()
        tournament = {
            "id": "test-event-for-dan-and-noam",
            "name": "Test Event for Dan and Noam",
            "startDate": far_future_epoch,
            "standings": [{"id": f"p{i}"} for i in range(32)],
            "rounds": [],
        }

        result = ingester.process_tournament(tournament)

        self.assertIsNone(result)
        supabase.upsert.assert_not_called()
        topdeck.get_tournament_tier.assert_not_called()

    def test_ingests_tournament_with_recent_start_date(self) -> None:
        supabase = Mock()
        supabase.table.return_value.upsert.return_value.execute.return_value.data = [{"id": "tournament-1"}]
        topdeck = Mock()
        topdeck.get_tournament_tier.return_value = None
        ingester = DataIngester(topdeck, supabase)

        recent_epoch = (datetime.now() - timedelta(days=1)).timestamp()
        tournament = {
            "id": "a-real-event",
            "name": "A Real Event",
            "startDate": recent_epoch,
            "standings": [],
            "rounds": [],
        }

        result = ingester.process_tournament(tournament)

        self.assertIsNotNone(result)
        self.assertTrue(supabase.table.return_value.upsert.called)


if __name__ == "__main__":
    unittest.main()
