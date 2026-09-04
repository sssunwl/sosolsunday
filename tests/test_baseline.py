import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from flight_scraper import (
    calculate_baseline,
    load_recent_flight_prices,
    write_flight_history,
)


class CalculateBaselineTests(unittest.TestCase):
    def test_empty_history_is_unknown(self):
        self.assertEqual(calculate_baseline([], 1200), {
            "n_days": 90,
            "samples": 0,
            "median": None,
            "p10": None,
            "min": None,
            "max": None,
            "percentile": None,
            "vs_median_pct": None,
            "verdict": "unknown",
        })

    def test_fewer_than_fourteen_samples_is_unknown_but_has_statistics(self):
        baseline = calculate_baseline([100, 200, 300], 200)

        self.assertEqual(baseline["samples"], 3)
        self.assertEqual(baseline["median"], 200)
        self.assertEqual(baseline["p10"], 120)
        self.assertEqual(baseline["min"], 100)
        self.assertEqual(baseline["max"], 300)
        self.assertEqual(baseline["percentile"], 33)
        self.assertEqual(baseline["vs_median_pct"], 0)
        self.assertEqual(baseline["verdict"], "unknown")

    def test_percentile_uses_strictly_lower_prices(self):
        baseline = calculate_baseline([100, 100, 200, 300], 100)

        self.assertEqual(baseline["percentile"], 0)

    def test_percentages_use_half_up_rounding(self):
        self.assertEqual(
            calculate_baseline(list(range(8)), 1)["percentile"], 13
        )
        self.assertEqual(
            calculate_baseline([200] * 14, 201)["vs_median_pct"], 1
        )
        self.assertEqual(
            calculate_baseline([200] * 14, 199)["vs_median_pct"], -1
        )

    def test_great_at_ten_percent_boundary(self):
        self.assertEqual(
            calculate_baseline(list(range(20)), 2)["verdict"], "great"
        )

    def test_good_at_thirty_percent_boundary(self):
        self.assertEqual(
            calculate_baseline(list(range(20)), 6)["verdict"], "good"
        )

    def test_normal_at_seventy_percent_boundary(self):
        self.assertEqual(
            calculate_baseline(list(range(20)), 14)["verdict"], "normal"
        )

    def test_high_above_seventy_percent(self):
        self.assertEqual(
            calculate_baseline(list(range(20)), 15)["verdict"], "high"
        )


class FlightHistoryTests(unittest.TestCase):
    def test_same_day_is_replaced_and_different_day_is_retained(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "nested", "flights.ndjson")
            fare = {
                ("HKG", "TPE"): {
                    "2026-02": {
                        "price": 100,
                        "date": "2026-02-10",
                        "return_at": "2026-02-14",
                        "airline_code": "UO",
                        "is_round_trip": False,
                    }
                }
            }

            write_flight_history(fare, date(2026, 1, 1), path)
            fare[("HKG", "TPE")]["2026-02"]["price"] = 110
            write_flight_history(fare, date(2026, 1, 1), path)
            fare[("HKG", "TPE")]["2026-02"]["price"] = 120
            write_flight_history(fare, date(2026, 1, 2), path)

            with open(path, encoding="utf-8") as history_file:
                records = [json.loads(line) for line in history_file]

            self.assertEqual(len(records), 2)
            self.assertEqual([record["p"] for record in records], [110, 120])
            self.assertEqual(list(records[0]), [
                "d", "o", "dst", "m", "p", "dep", "ret", "al", "rt"
            ])
            self.assertEqual(records[0]["ret"], "2026-02-14")
            self.assertFalse(records[0]["rt"])
            self.assertEqual(
                load_recent_flight_prices(date(2026, 1, 2), path),
                {("HKG", "TPE", "2026-02"): [110, 120]},
            )

    def test_recent_prices_use_inclusive_ninety_day_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "flights.ndjson")
            as_of = date(2026, 1, 1)
            cutoff = as_of - timedelta(days=90)
            fare = {
                ("HKG", "TPE"): {
                    "2026-02": {
                        "price": 0,
                        "date": "2026-02-10",
                        "return_at": None,
                        "airline_code": "UO",
                        "is_round_trip": False,
                    }
                }
            }
            observations = [
                (cutoff - timedelta(days=1), 100),
                (cutoff, 200),
                (as_of, 300),
                (as_of + timedelta(days=1), 400),
            ]
            for scrape_date, price in observations:
                fare[("HKG", "TPE")]["2026-02"]["price"] = price
                write_flight_history(fare, scrape_date, path)

            self.assertEqual(
                load_recent_flight_prices(as_of, path),
                {("HKG", "TPE", "2026-02"): [200, 300]},
            )


if __name__ == "__main__":
    unittest.main()
