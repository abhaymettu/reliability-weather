import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from weather.harness import act, parse_action, run_episode  # noqa: E402
from weather.providers import run_cost  # noqa: E402


class Scripted:
    def __init__(self, replies):
        self.replies = list(replies)

    def send(self, system, messages):
        return self.replies.pop(0), {"cost_usd": 0.001}


class Harness(unittest.TestCase):
    def test_parse_tolerates_fences_and_prose(self):
        self.assertEqual(parse_action('Sure.\n```json\n{"action": "read", "path": "a.py"}\n```'),
                         {"action": "read", "path": "a.py"})
        self.assertIsNone(parse_action('{"path": "a.py"}'))

    def test_write_outside_project_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d).resolve()
            self.assertTrue(act(w, {"action": "write", "path": "../x.txt", "content": "x"}).startswith("error"))
            self.assertFalse((w.parent / "x.txt").exists())

    def test_run_reads_nothing_under_users(self):
        with tempfile.TemporaryDirectory() as d:
            out = act(Path(d).resolve(), {"action": "run", "args": ["-c", "open('/Users/Shared/../' ).read()"]})
            self.assertIn("Operation not permitted", out)

    def test_episode_stops_at_budget_and_keeps_files(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            ep = run_episode(Scripted(['{"action": "write", "path": "f.txt", "content": "hi"}', "no action here",
                                       '{"action": "list"}', '{"action": "list"}']), "task", w, max_turns=3)
            self.assertEqual((ep["ended"], len(ep["turns"])), ("turn_limit", 3))
            self.assertEqual((w / "f.txt").read_text(), "hi")
            self.assertTrue(ep["turns"][1]["result"].startswith("error: reply was not"))

    def test_claude_run_cost_is_the_session_total(self):
        calls = [{"total_cost_usd": 0.003, "cost_usd": 0.003}, {"total_cost_usd": 0.009, "cost_usd": 0.006}]
        self.assertEqual(run_cost(calls), 0.009)
        self.assertEqual(run_cost([{"cost_usd": 0.25}, {"cost_usd": 0.5}]), 0.75)


if __name__ == "__main__":
    unittest.main()
