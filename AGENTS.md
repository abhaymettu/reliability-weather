# AGENTS.md

Python 3.12+, standard library only, macOS (the sandbox is `sandbox-exec`).

## Checks

- `python3 tests/validate_battery.py` prints `30 tasks, 0 bad`: every task fails on its starting files and passes with its reference solution.
- `python3 -m unittest tests.test_stats tests.test_harness` passes.
- `python3 -m weather.publish` rebuilds `docs/` and the README's top block from `runs/`; run it after any change to the page or the statistics.

## Rules

- Never edit `battery/v1/`, `weather/harness.py`'s prompt or turn budget, or the statistics in place. A change to any of them starts a new series (`battery/v2`) and a line in `PREREGISTRATION.md` section 8.
- Receipts under `runs/` are data. Do not rewrite them; rerunning a day only fills runs that are missing or hit an infrastructure error.
- `runs/pilot/` never reaches the page. Only folders named as dates do.
- No number on the page or in the README is typed by hand; `weather/page.py` renders them from the feed.
- Machine settings live in `.state/` and stay out of git: `branch` (what the daily job checks out), `models` (default `sonnet,haiku`), `claude-config-dir` (which Claude login).
- The DeepSeek key is read from `~/.local/share/opencode/auth.json` at call time. Never print it or write it anywhere.
