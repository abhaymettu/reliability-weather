# reliability weather

<!-- weather:start -->
**November 6, 2026. Claude Haiku passed 99% of its 150 runs (95% interval 95 to 100). Run the same 30 tasks once instead of 5 times and DeepSeek Flash could have scored anywhere from 73% to 97%.**

| Model | Pass rate | 95% interval | One run could score | Tasks that flipped |
| --- | --- | --- | --- | --- |
| Claude Haiku | 99% | 95 to 100 | 97 to 100 | 1 of 30 |
| Claude Sonnet | 97% | 93 to 99 | 93 to 100 | 3 of 30 |
| DeepSeek Flash | 85% | 79 to 90 | 73 to 97 | 12 of 30 |
<!-- weather:end -->

**[Today's page](https://abhaymettu.github.io/reliability-weather/)** · [feed.json](https://abhaymettu.github.io/reliability-weather/feed.json) · [preregistration](PREREGISTRATION.md)

Agent leaderboards report one run per task. Run the same agent on the same task again and it can pass where it
failed, or fail where it passed. This repository measures that every day. A fixed battery of 30 small coding and
tool-use tasks runs 5 times per model, through one harness, and a deterministic check grades the files each run leaves
behind. The page reports each model's pass rate with a 95% interval, the range a single run of the battery could have
scored, the share of variation that is run-to-run noise, and whether today differs from the last day.

It follows [agent-run-reliability](https://github.com/abhaymettu/agent-run-reliability), a one-off study of 384 Claude
Code runs in which run-to-run noise was 50.1% of outcome variance.

## What runs

| Part | File | What it does |
| --- | --- | --- |
| Battery v1 | `battery/v1/*.py` | 30 tasks: 8 repairs, 8 implementations from a contract, 8 data jobs, 6 multi-file chores. Each has starting files, a prompt, a reference solution and a hidden check |
| Harness | `weather/harness.py` | One JSON action per turn (list, read, write, run python3, finish), 4 turns, the same messages to every model |
| Sandbox | `weather/sandbox.py` | Model-written code runs under `sandbox-exec`, which blocks the network and the home folder and allows writes only in the run's temp directory |
| Providers | `weather/providers.py` | Claude Sonnet and Haiku through `claude -p` with no tools; DeepSeek V4 Pro and Flash through the DeepSeek API |
| Runner | `weather/run.py` | Runs a day, writes one receipt per run, skips runs that already have one, retries provider failures, stops at a daily cost cap |
| Statistics | `weather/stats.py` | Wilson interval, Newcombe change test, exact one-run range, run-to-run variance share, flip rate |
| Publisher | `weather/publish.py`, `weather/page.py` | Builds `docs/feed.json`, `docs/days/<date>.json`, `docs/index.html` and the numbers at the top of this file from the receipts |
| Schedule | `scripts/daily.sh` | The daily job, run by launchd on the machine that holds the model logins |

Every run's receipt, under `runs/<date>/<model>/<task>/r<k>.json`, holds the transcript, each call's usage object
as the provider returned it, the check's verdict and the list-price cost.

## Run it

Python 3.12 or newer, standard library only, on macOS (the sandbox uses `sandbox-exec`).

```sh
python3 tests/validate_battery.py          # every task fails on its starting files and passes with its solution
python3 -m unittest tests.test_stats       # the statistics against hand-checked values
python3 -m weather.run --date 2026-11-04 --n 5 --models sonnet,haiku   # needs claude -p; DeepSeek needs a key
python3 -m weather.publish                 # rebuild the feed, the page and this README's numbers
```

The DeepSeek key is read at call time from `~/.local/share/opencode/auth.json` (`{"deepseek": {"key": ...}}`) and
never written anywhere else. `scripts/install-schedule.sh` installs the daily launchd job for a checkout.

## What the numbers mean

The pass rate is passes over runs, 150 runs per model per day. Its 95% interval is the Wilson score interval on those
runs. Inference is about this battery, so the only randomness is rerunning, and pooling across tasks makes the
interval conservative.

"One run could score" is the middle 95% of scores a single run per task would get, each task passing at its observed
rate. It is the spread a single-run leaderboard hides. The run-to-run share of variance is the part of the variation in
single-run outcomes that comes from rerunning the same model on the same task, rather than from tasks differing in
difficulty.

A model has moved when the 95% interval for the change since its last complete day excludes zero. With four models a
day, expect about one false alarm every five days.

The 4-turn budget is part of what is measured: the battery asks for a correct change in few actions. At 10 turns the
pilot passed 117 of 119 runs, which leaves nothing to measure; how the budget was chosen is in the preregistration.

## Limits

- 30 tasks is a small battery, built to be cheap enough to run every day. The pass rate describes this battery, not
  coding in general.
- Claude runs through `claude -p`, which adds its own small Haiku call per session; the page reports the model that did
  the work.
- Claude Code tells Claude models about a working folder and a scratch folder of its own, outside the task, even with
  its system prompt replaced. Haiku sometimes writes there; the write is refused and costs a turn. On the first day
  that was 24 Haiku runs and 6 of its 7 failures. DeepSeek gets no such hint. Battery v1 keeps the harness fixed, so it
  stays in the numbers, and the page counts it every day.
- A model provider can change what a model name serves without notice. The page lists the model ids actually served.

## License

MIT for the code. STIX Two Text, in `docs/fonts/`, is under the SIL Open Font License.
