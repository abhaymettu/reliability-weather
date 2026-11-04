import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from weather import stats  # noqa: E402

SPLIT = {"a": (5, 5), "b": (0, 5)}
MIXED = {"a": (2, 5)}


class Stats(unittest.TestCase):
    def test_pass_rate_weights_tasks_equally(self):
        self.assertEqual(stats.pass_rate({"a": (5, 5), "b": (1, 10)}), 0.55)

    def test_noise_share_zero_when_tasks_never_flip(self):
        self.assertEqual(stats.noise_share(SPLIT), 0.0)

    def test_noise_share_one_for_a_single_flipping_task(self):
        self.assertEqual(stats.noise_share(MIXED), 1.0)

    def test_noise_share_undefined_without_variance(self):
        self.assertIsNone(stats.noise_share({"a": (5, 5), "b": (5, 5)}))

    def test_flip_rate(self):
        self.assertEqual(stats.flip_rate({"a": (5, 5), "b": (3, 5), "c": (0, 5), "d": (1, 5)}), 0.5)

    def test_interval_brackets_estimate_and_is_reproducible(self):
        s1 = stats.summarize(SPLIT, "2026-11-04", "m")
        s2 = stats.summarize(SPLIT, "2026-11-04", "m")
        self.assertEqual(s1, s2)
        self.assertEqual([round(x, 4) for x in s1["interval95"]], [0.2366, 0.7634])
        self.assertEqual(s1["one_run_range95"], [0.5, 0.5])

    def test_perfect_score_interval_stays_below_one(self):
        lo, hi = stats.summarize({t: (5, 5) for t in "abcdefghij"}, "d", "m")["interval95"]
        self.assertEqual((round(lo, 4), hi), (0.9287, 1.0))

    def test_one_run_range_of_coin_flips(self):
        self.assertEqual(stats.one_run_range({t: (1, 2) for t in "abcd"}), (0.0, 1.0))
        self.assertEqual(stats.one_run_range({t: (1, 2) for t in "abcdefghijklmnopqrst"}), (0.3, 0.7))

    def test_change_flags_a_big_drop_and_not_a_tie(self):
        hi_day = {t: (5, 5) for t in "abcdefghij"}
        lo_day = {t: (1, 5) for t in "abcdefghij"}
        self.assertTrue(stats.change(lo_day, hi_day)["moved"])
        self.assertFalse(stats.change(hi_day, hi_day)["moved"])


if __name__ == "__main__":
    unittest.main()
