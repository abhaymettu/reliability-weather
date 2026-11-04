"""Turn receipts into the feed (docs/feed.json, docs/days/<date>.json) and the page (docs/index.html).

Only folders named as dates count; pilot and other labels never reach the weather. A day is published for a
model once every task in the battery has the preregistered number of runs with a pass or fail outcome.
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import battery, providers, stats
from .run import RUNS, read_receipt

REPO = RUNS.parent
DOCS = REPO / "docs"
N_PER_DAY = 5
MODELS = {
    "sonnet": {"name": "Claude Sonnet", "provider": "Anthropic, through claude -p", "shape": "circle"},
    "haiku": {"name": "Claude Haiku", "provider": "Anthropic, through claude -p", "shape": "square"},
    "deepseek-v4-pro": {"name": "DeepSeek V4 Pro", "provider": "DeepSeek API", "shape": "diamond"},
    "deepseek-flash": {"name": "DeepSeek Flash", "provider": "DeepSeek API", "shape": "triangle"},
}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def collect(label: str) -> dict:
    """{model: {"counts": {task: (k, n)}, "cost_usd", "infra_errors", "turns", "versions"}} for one day folder."""
    out = defaultdict(lambda: {"counts": defaultdict(lambda: [0, 0]), "cost_usd": 0.0, "infra_errors": 0,
                               "turns": [], "outside_writes": [0, 0], "served": set(), "battery_sha256": set(), "by_cat": defaultdict(lambda: [0, 0])})
    for p in sorted((RUNS / label).glob("*/*/r*.json")):
        r = read_receipt(p)
        if not r:
            continue
        m = out[r["model"]]
        m["battery_sha256"].add(r["battery_sha256"])
        if r["outcome"] == "infra_error":
            m["infra_errors"] += 1
            continue
        c = m["counts"][r["task"]]
        c[0] += r["outcome"] == "pass"
        c[1] += 1
        cat = m["by_cat"][r["category"]]
        cat[0] += r["outcome"] == "pass"
        cat[1] += 1
        m["cost_usd"] += providers.run_cost(r.get("calls", []))
        m["turns"].append(r["turns_used"])
        if any((t["result"] or "").startswith("error: write needs a path inside") for t in r["transcript"]):
            m["outside_writes"][0] += 1
            m["outside_writes"][1] += r["outcome"] == "fail"
        for call in r.get("calls", []):
            # Claude Code adds one small Haiku call per session for itself; the subject is the most-used model.
            usage = call.get("modelUsage") or {}
            served = call.get("model") or max(usage, key=lambda k: usage[k].get("costUSD", 0), default=None)
            if served:
                m["served"].add(served)
    return out


def day_summary(label: str, task_ids: list[str]) -> dict:
    models = {}
    for model, m in collect(label).items():
        counts = {t: tuple(m["counts"][t]) for t in task_ids if t in m["counts"]}
        complete = len(counts) == len(task_ids) and all(n == N_PER_DAY for _, n in counts.values())
        if not counts:
            continue
        s = stats.summarize(counts, label, model)
        models[model] = {
            **s,
            "complete": complete,
            "by_category": {c: {"passes": k, "runs": n, "pass_rate": k / n} for c, (k, n) in sorted(m["by_cat"].items())},
            "tasks_detail": {t: {"passes": k, "runs": n} for t, (k, n) in sorted(counts.items())},
            "mean_turns": sum(m["turns"]) / len(m["turns"]),
            "cost_usd_list_price": round(m["cost_usd"], 4),
            "infra_errors": m["infra_errors"],
            "runs_with_refused_outside_write": m["outside_writes"][0],
            "failed_runs_with_refused_outside_write": m["outside_writes"][1],
            "served_model_ids": sorted(m["served"]),
            "battery_sha256": sorted(m["battery_sha256"]),
            "_counts": counts,
        }
    return models


def build(version: str = "v1") -> dict:
    task_ids = [t.id for t in battery.load(version)]
    labels = sorted(p.name for p in RUNS.iterdir() if p.is_dir() and DATE.match(p.name))
    days = []
    for label in labels:
        ms = day_summary(label, task_ids)
        if ms:
            days.append({"date": label, "models": ms})
    for i, d in enumerate(days):
        for model, s in d["models"].items():
            prev = next((p for p in reversed(days[:i]) if model in p["models"] and p["models"][model]["complete"]), None)
            if prev and s["complete"]:
                s["change"] = {"vs": prev["date"], **stats.change(s["_counts"], prev["models"][model]["_counts"])}
    for d in days:
        for s in d["models"].values():
            del s["_counts"]
    feed = {
        "name": "reliability weather",
        "battery": version,
        "battery_sha256": battery.digest(version),
        "tasks": len(task_ids),
        "task_ids": task_ids,
        "runs_per_task_per_day": N_PER_DAY,
        "statistic": "pass rate over all runs; Wilson 95% interval; day-over-day change by Newcombe's hybrid score "
        "interval (PREREGISTRATION.md section 4)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "models": MODELS,
        "latest": days[-1]["date"] if days else None,
        "days": days,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "days").mkdir(exist_ok=True)
    for d in days:
        (DOCS / "days" / f"{d['date']}.json").write_text(json.dumps(d, indent=1) + "\n")
    (DOCS / "feed.json").write_text(json.dumps(feed, indent=1) + "\n")
    from .page import readme_block, render

    (DOCS / "index.html").write_text(render(feed))
    readme = REPO / "README.md"
    text = readme.read_text()
    start, end = "<!-- weather:start -->", "<!-- weather:end -->"
    head, rest = text.split(start, 1)
    readme.write_text(head + start + "\n" + readme_block(feed) + "\n" + end + rest.split(end, 1)[1])
    return feed


if __name__ == "__main__":
    f = build()
    last = f["days"][-1]["models"] if f["days"] else {}
    print("; ".join(f"{f['models'][m]['name']} {s['passes']}/{s['runs']}" for m, s in last.items()))
