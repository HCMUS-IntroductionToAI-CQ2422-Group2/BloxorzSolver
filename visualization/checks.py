"""Run with: python -m unittest visualization.checks -v (viz environment)."""

import csv
from pathlib import Path
import statistics
import tempfile
import unittest

from visualization.benchmark_plots import (
    ALGORITHMS, MAPS, load_benchmark, paired_ratios, summary_table,
)


class BenchmarkVisualizationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path(__file__).resolve().parents[1] / "benchmarks/benchmark_20_maps.csv"
        cls.data = load_benchmark(cls.path)
        with cls.path.open(newline="", encoding="utf-8") as source:
            cls.raw = list(csv.DictReader(source))

    def assert_rejected(self, mutate, message):
        rows = [dict(row) for row in self.raw]
        mutate(rows)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "modified.csv"
            with path.open("w", newline="", encoding="utf-8") as target:
                writer = csv.DictWriter(target, fieldnames=list(self.raw[0]))
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, message):
                load_benchmark(path)

    def test_summary_matches_independent_raw_calculations(self):
        summary = summary_table(self.data)
        for algorithm in ALGORITHMS:
            rows = [row for row in self.raw if row["algorithm"] == algorithm]
            self.assertEqual(summary.loc[algorithm, "solved_maps"], 20)
            self.assertAlmostEqual(summary.loc[algorithm, "median_time_s"],
                                   statistics.median(float(row["search_time_s"]) for row in rows))
            self.assertAlmostEqual(summary.loc[algorithm, "median_memory_mib"],
                                   statistics.median(int(row["peak_memory_bytes"]) / 1048576 for row in rows))

    def test_ratios_pair_the_same_map_before_aggregation(self):
        for metric in ("search_time_s", "peak_memory_bytes", "expanded_nodes", "solution_length"):
            result = paired_ratios(self.data, metric)
            for algorithm in ALGORITHMS:
                expected = []
                for map_id in MAPS:
                    by_algorithm = {row["algorithm"]: float(row[metric])
                                    for row in self.raw if row["map_id"] == map_id}
                    ratio = by_algorithm[algorithm] / by_algorithm["BFS"]
                    expected.append(ratio)
                    self.assertAlmostEqual(result.loc[map_id, algorithm], ratio)
                self.assertAlmostEqual(result[algorithm].median(), statistics.median(expected))

    def test_duplicate_key_is_rejected(self):
        self.assert_rejected(lambda rows: rows.append(dict(rows[0])), "Duplicate")

    def test_missing_map_algorithm_pair_is_rejected(self):
        self.assert_rejected(lambda rows: rows.pop(), "20 maps")

    def test_mixed_runs_are_rejected(self):
        self.assert_rejected(lambda rows: rows[0].update(run_id="different-run"), "run_id")

    def test_invalid_replay_is_rejected(self):
        self.assert_rejected(lambda rows: rows[0].update(solution_valid="false"), "replay")

    def test_wrong_path_cost_is_rejected(self):
        self.assert_rejected(lambda rows: rows[0].update(path_cost="999"), "path_cost")

    def test_unavailable_measurement_is_not_replaced_by_zero(self):
        self.assert_rejected(lambda rows: rows[0].update(search_time_s=""), "missing measurements")


if __name__ == "__main__":
    unittest.main()
