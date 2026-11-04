# Preregistration: reliability weather, battery v1

Frozen at the commit that adds this file, before the first counted run (2026-11-04). Anything below that changes
later is logged in section 8 with its date and reason, and a change to the battery, the harness prompt or the turn
budget starts a new series (battery v2) instead of editing v1.

## 1. Question

How reliable is a coding agent from one day to the next, and how much of a single-run score is noise? Every day, a
fixed battery runs a fixed number of times per model through one harness, and the page reports each model's pass rate
with an interval, the share of variation that is run-to-run noise, and whether today differs from the last day.

This follows [agent-run-reliability](https://github.com/abhaymettu/agent-run-reliability), where 384 Claude Code runs
put run-to-run noise at 50.1% of outcome variance. That study was a one-off; this one repeats daily and adds models
from a second provider.

## 2. Battery v1

- 30 tasks in four categories: 8 `codefix` (repair a module to a stated contract), 8 `implement` (write a module
  from a contract), 8 `data` (read files, compute an exact result, write an output file), 6 `chore` (multi-file
  changes: rename, split a module, untangle a circular import, add a CLI, bump a version, make tests green).
- Source: `battery/v1/*.py`. The battery's sha256 over those files is recorded in every run receipt. Value at
  freeze: `b407a8cf9f16863d670d00d6aa27b846f4ec301dd8485bae4625d672a3bb0ffe`.
- Each task has a prompt, starting files, a reference solution and a deterministic check. `tests/validate_battery.py`
  asserts, for every task, that the check fails on the starting files and passes with the reference solution. At
  freeze it printed `30 tasks, 0 bad`.
- Checks never call a model. Checks that run model-written code do so in the same sandbox as the model's own runs.

## 3. Harness and models

- One harness for every model (`weather/harness.py`): a system prompt that defines five JSON actions (list, read,
  write, run python3, finish), one action per turn, at most 4 turns, then grading. The files are graded as they stand when the model finishes or the turns run out, so a model need not spend a turn on finish. Every provider receives the same
  messages, so the model is the only thing that differs between rows.
- Code the model runs executes under macOS `sandbox-exec`: no network, no reads under `/Users`, writes only inside the
  run's temporary directory, 10 seconds per command.
- Models, each at its provider's default sampling settings (no temperature or thinking override):
  - `sonnet` and `haiku`: Claude through `claude -p` with no tools, no user settings and the harness system prompt
    (`claude-batch`), one resumed session per run. The model id actually served is recorded per call.
  - `deepseek-v4-pro` and `deepseek-flash`: the DeepSeek API, OpenAI-compatible chat completions.
- Opus is not in the daily set: its list price would dominate the daily budget without a question that needs it.

## 4. Statistics

Per model per day, over the 30 tasks with n runs each:

- **Pass rate**: passes divided by runs. With every task at n runs this equals the mean of per-task pass rates.
- **Primary interval**: the Wilson score 95% interval on passes out of runs. Inference is about this battery, so the
  only randomness is run to run, and pooling runs across tasks makes the interval conservative (stratifying by task
  can only shrink the variance).
- **Secondary interval**: a two-stage bootstrap (tasks with replacement, then runs within each task), 5,000
  resamples, seeded from the date and model, for readers who want to generalize to similar tasks.
- **One-run range**: the 2.5th to 97.5th percentiles of the battery score a single run per task would get, each task
  passing at its observed rate (exact Poisson-binomial). This is the spread a single-run leaderboard hides.
- **Run-to-run share of variance**: the mean over tasks of the unbiased within-task Bernoulli variance
  k(n-k)/(n(n-1)), divided by the unbiased variance of all outcomes pooled. Undefined when every outcome agrees.
- **Flip rate**: the share of tasks whose n runs do not all agree.
- **Change**: today's pass rate minus that of the most recent earlier complete day, with Newcombe's hybrid score 95%
  interval. A model is marked "moved" when that interval excludes zero. Four models a day means about one false
  "moved" every five days by chance alone; the page says so and nothing else corrects for it.
- Category pass rates are reported as description, without intervals or tests.

## 5. Design

- n = 5 runs per task per model per day, so 150 runs per model per day and 600 in all.
- Runs are scheduled with the run index outermost, so a stopped day still has the same number of runs on every task.
- A day is "complete" for a model when all 30 tasks have 5 runs with a pass or fail outcome. Only complete days get a
  change test.
- The daily job starts at 04:30 America/Chicago (the machine's clock) and labels the day by its UTC date.

## 6. Outcomes and exclusions

- A run passes when the task's check returns true on the files left when the model finishes or the turns run out.
  A reply that is not a parseable action uses a turn and is the model's failure, not an exclusion.
- An infrastructure error (the provider times out, returns 5xx or 429 after four tries, or returns an envelope that
  cannot be read) is not an outcome. The run is retried in up to two more passes that day; if it still fails it is
  missing, the day is incomplete for that model, and the count of infrastructure errors is published.
- Pilot runs (folder `runs/pilot/`, one run per task per model at a 10-turn budget, 2026-11-04) tested the plumbing
  and cost before the freeze. They are excluded from the weather and kept in the repository.
- The turn budget was set from the pilot, before any counted run. At 10 turns the pilot passed 117 of 119 graded runs,
  which leaves nothing to measure. `scripts/replay_budget.py` replays each pilot transcript cut at B turns and
  re-checks it: pooled pass rates were 64% at 3 turns, 79% at 4, 87% at 5, 89% at 6 and 98% at 10. The budget is 4,
  the largest at which the replayed rate stays under 85%. The replay is a lower bound, because a model told it has 4
  turns can plan for them. The budget is part of what is measured: the battery asks for a correct change in few
  actions, and the page says so.

## 7. Budget

- List-price cap per day: $10 for Claude (on the subscription, so no money changes hands; the figure is what the same
  calls would cost on the API, from `claude -p`'s own cost field) and $1.50 for DeepSeek (real spend, priced from
  api-docs.deepseek.com on 2026-11-04, peak and off-peak hours applied per call). A provider that reaches its cap stops
  starting runs for the day, which leaves the day incomplete rather than unbalanced.
- Every call's usage object is stored verbatim in its run receipt.

## 8. Deviations and observations

No deviations. Observation after the first day (2026-11-04), not a change: `claude -p` tells the model about its own
working folder and a scratch folder even with the system prompt replaced. Claude Haiku wrote to that scratch folder in
24 of 150 runs; each such write was refused and cost a turn, and those runs hold 6 of its 7 failures. The analysis is
unchanged. The publisher counts refused outside writes per model per day so the effect stays visible, and removing the
hint would start battery v2.
