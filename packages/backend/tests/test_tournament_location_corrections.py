import unittest

from tournament_location_corrections import CORRECTIONS, corrected_location


class ReviewedLocationTests(unittest.TestCase):
    def test_all_reviewed_events_resolve_and_are_idempotent(self):
        self.assertEqual(len({r["topdeck_tid"] for r in CORRECTIONS}), len(CORRECTIONS))
        for row in CORRECTIONS:
            with self.subTest(event=row["topdeck_tid"]):
                original = {
                    "city": row["city"],
                    "venue": row["venue"],
                    "state": row["original_state"],
                    "country": row["original_country"],
                }
                result = corrected_location(row["topdeck_tid"], original)
                self.assertEqual((result["state"], result["country"]), (row["state"], row["country"]))
                self.assertEqual(corrected_location(row["topdeck_tid"], result), result)

    def test_changed_source_or_unknown_event_is_not_overridden(self):
        row = next(r for r in CORRECTIONS if r["original_state"] == "WA")
        original = {"city": row["city"], "venue": row["venue"], "state": "WA", "country": None}
        for key, value in [
            ("city", "Perth"),
            ("venue", "A different venue"),
            ("country", "Australia"),
            ("state", "Oregon"),
        ]:
            changed = {**original, key: value}
            self.assertEqual(corrected_location(row["topdeck_tid"], changed), changed)
        self.assertEqual(corrected_location("unreviewed-event", original), original)

    def test_us_repairs_have_explicit_us_address_evidence(self):
        for row in CORRECTIONS:
            if row["country"] == "United States":
                self.assertTrue(row["venue"].endswith(", USA"))
                code = "WA" if row["state"] == "Washington" else "CA"
                self.assertRegex(row["venue"], r", " + code + r"(?:,| \d{5},) USA$")


if __name__ == "__main__":
    unittest.main()
