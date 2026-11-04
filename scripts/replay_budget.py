"""Calibration aid: replay pilot transcripts cut at B turns and re-check. A lower bound on the pass rate at budget B,
because a model told it has fewer turns may plan for them."""
import collections
import glob
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from weather import battery  # noqa: E402
from weather.harness import act, parse_action  # noqa: E402

tasks = {t.id: t for t in battery.load("v1")}
res = collections.defaultdict(lambda: collections.Counter())
for p in glob.glob("runs/pilot/*/*/r0.json"):
    r = json.loads(Path(p).read_text())
    if r["outcome"] == "infra_error":
        continue
    t = tasks[r["task"]]
    for budget in (3, 4, 5, 6, 10):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d).resolve()
            t.materialize(w)
            for turn in r["transcript"][:budget]:
                a = parse_action(turn["reply"])
                if a and a.get("action") != "finish":
                    act(w, a)
            ok, _ = t.check(w)
        res[budget][r["model"]] += ok
        res[budget]["_all"] += ok
        res[budget]["_n_" + r["model"]] += 1
        res[budget]["_n"] += 1
for b in sorted(res):
    c = res[b]
    print(b, f"all {c['_all']}/{c['_n']} = {c['_all'] / c['_n']:.2f}",
          {m: f"{c[m]}/{c['_n_' + m]}" for m in ("sonnet", "haiku", "deepseek-v4-pro", "deepseek-flash")})
