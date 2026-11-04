"""Run the battery n times per model for one day. Idempotent: a run with a pass or fail receipt is never redone.

  python3 -m weather.run --date 2026-11-04 --n 5 --models sonnet,haiku,deepseek-flash,deepseek-v4-pro
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import battery, providers
from .harness import MAX_TURNS, SYSTEM, run_episode

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
SCHEMA = 1
# List-price dollars per day, per provider. Claude runs on the subscription; its list-price figure is what the same
# calls would cost on the API, recorded from claude -p's own total_cost_usd.
DAILY_CAP_USD = {"claude": 10.00, "deepseek": 1.50}


def provider_family(model: str) -> str:
    return "claude" if model in ("sonnet", "haiku") else "deepseek"


def receipt_path(label: str, model: str, task_id: str, k: int) -> Path:
    return RUNS / label / model / task_id / f"r{k}.json"


def read_receipt(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_atomic(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, p)


def repo_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


class Spend:
    """Running list-price spend per provider family for the day, seeded from receipts already on disk."""

    def __init__(self, label: str):
        self.lock = threading.Lock()
        self.usd = {f: 0.0 for f in DAILY_CAP_USD}
        for p in (RUNS / label).glob("*/*/r*.json"):
            r = read_receipt(p)
            if r:
                self.usd[provider_family(r["model"])] += providers.run_cost(r.get("calls", []))

    def over(self, family: str) -> bool:
        with self.lock:
            return self.usd[family] >= DAILY_CAP_USD[family]

    def add(self, family: str, usd: float) -> None:
        with self.lock:
            self.usd[family] += usd


def one_run(label: str, version: str, sha: str, commit: str, task: battery.Task, model: str, k: int,
            spend: Spend) -> str:
    path = receipt_path(label, model, task.id, k)
    old = read_receipt(path)
    if old and old["outcome"] in ("pass", "fail"):
        return "skip"
    family = provider_family(model)
    if spend.over(family):
        return "cap"
    started = datetime.now(timezone.utc)
    base = {
        "schema": SCHEMA, "label": label, "battery": version, "battery_sha256": sha, "repo_commit": commit,
        "model": model, "task": task.id, "category": task.category, "run": k, "max_turns": MAX_TURNS,
        "started_utc": started.isoformat(timespec="seconds"), "python": platform.python_version(),
    }
    with tempfile.TemporaryDirectory(prefix="rw-") as d:
        work = Path(d)
        task.materialize(work)
        provider = providers.make(model)
        try:
            ep = run_episode(provider, task.prompt, work)
        except providers.InfraError as e:
            write_atomic(path, {**base, "outcome": "infra_error", "error": str(e)[:500], "cost_usd": 0.0,
                                "attempts": (old or {}).get("attempts", 0) + 1})
            return "infra_error"
        ok, detail = task.check(work)
    cost = providers.run_cost(ep["calls"])
    spend.add(family, cost)
    write_atomic(path, {
        **base, "outcome": "pass" if ok else "fail", "check_detail": detail, "ended": ep["ended"],
        "turns_used": len(ep["turns"]), "cost_usd": cost,
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "calls": ep["calls"], "transcript": ep["turns"],
    })
    return "pass" if ok else "fail"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat(),
                    help="the day's label; receipts go to runs/<date>/")
    ap.add_argument("--label", help="override the folder label, e.g. pilot (excluded from the weather)")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--models", default="sonnet,haiku,deepseek-flash,deepseek-v4-pro")
    ap.add_argument("--battery", default="v1")
    ap.add_argument("--tasks", help="comma-separated task ids (pilot only)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--retries", type=int, default=2, help="extra passes over runs that hit an infra error")
    a = ap.parse_args(argv)

    label = a.label or a.date
    tasks = battery.load(a.battery)
    if a.tasks:
        keep = set(a.tasks.split(","))
        tasks = [t for t in tasks if t.id in keep]
    models = a.models.split(",")
    sha, commit = battery.digest(a.battery), repo_commit()
    # Run index outermost, so a cap or a crash leaves every task with the same number of runs per model.
    jobs = [(t, m, k) for k in range(a.n) for t in tasks for m in models]
    spend = Spend(label)
    counts: dict[str, int] = {}
    t0 = time.time()
    for attempt in range(1 + a.retries):
        with ThreadPoolExecutor(a.workers) as pool:
            results = list(pool.map(lambda j: one_run(label, a.battery, sha, commit, *j, spend), jobs))
        counts = {s: results.count(s) for s in set(results)}
        print(f"pass {attempt + 1}: {counts} spend {spend.usd} in {time.time() - t0:.0f} s", flush=True)
        if not counts.get("infra_error"):
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
