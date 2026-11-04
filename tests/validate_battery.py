"""Every task must fail on its starting files and pass with its reference solution. Exit 0 only if all do."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from weather.battery import digest, load  # noqa: E402

version = sys.argv[1] if len(sys.argv) > 1 else "v1"
bad = 0
tasks = load(version)
for t in tasks:
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        t.materialize(Path(a))
        t.materialize(Path(b), with_solution=True)
        start_ok, start_why = t.check(Path(a))
        sol_ok, sol_why = t.check(Path(b))
    verdict = "ok" if (not start_ok and sol_ok) else "BAD"
    bad += verdict == "BAD"
    print(f"{verdict:3} {t.category:9} {t.id:24} start={'pass' if start_ok else 'fail'} solution={'pass' if sol_ok else 'fail'}"
          + ("" if verdict == "ok" else f"  [{start_why if start_ok else sol_why}]"))
print(f"{len(tasks)} tasks, {bad} bad, battery {version} sha256 {digest(version)}")
sys.exit(1 if bad else 0)
