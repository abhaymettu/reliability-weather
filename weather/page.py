"""Render docs/index.html from the feed. Every number on the page comes from the feed; none is typed by hand."""
import html
from datetime import date

# Okabe-Ito, picked so the pairs differ in lightness as well as hue; shape and a text label carry the same meaning.
COLOR = {"sonnet": "#0072B2", "haiku": "#56B4E9", "deepseek-v4-pro": "#D55E00", "deepseek-flash": "#E69F00"}
COLOR_DARK = {"sonnet": "#4FA3E0", "haiku": "#9AD3F5", "deepseek-v4-pro": "#F08A4B", "deepseek-flash": "#F5C04A"}


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def pct_n(x: float) -> str:
    return f"{100 * x:.0f}"


def nice_date(s: str) -> str:
    d = date.fromisoformat(s)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def marker(shape: str, x: float, y: float, r: float, cls: str) -> str:
    if shape == "circle":
        return f'<circle class="{cls}" cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'
    if shape == "square":
        return f'<rect class="{cls}" x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}"/>'
    if shape == "diamond":
        q = r * 1.3
        return f'<path class="{cls}" d="M{x:.1f} {y - q:.1f}L{x + q:.1f} {y:.1f}L{x:.1f} {y + q:.1f}L{x - q:.1f} {y:.1f}Z"/>'
    q = r * 1.25
    return f'<path class="{cls}" d="M{x:.1f} {y - q:.1f}L{x + q:.1f} {y + q * 0.8:.1f}L{x - q:.1f} {y + q * 0.8:.1f}Z"/>'


def today_figure(feed: dict, day: dict) -> str:
    rows = sorted(day["models"].items(), key=lambda kv: -kv[1]["pass_rate"])
    lo = min(min(s["one_run_range95"][0], s["interval95"][0]) for _, s in rows)
    x0 = max(0.0, (int(lo * 10) / 10) - 0.1)
    w, left, right, row_h, top = 820, 170, 150, 56, 28
    plot = w - left - right
    h = top + row_h * len(rows) + 34

    def X(v):
        return left + plot * (v - x0) / (1 - x0)

    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="f1t f1d" class="fig">',
           '<title id="f1t">Pass rate today, by model</title>',
           '<desc id="f1d">' + html.escape("; ".join(
               f"{feed['models'][m]['name']}: {pct(s['pass_rate'])}, 95% interval {pct_n(s['interval95'][0])} to "
               f"{pct_n(s['interval95'][1])}, a single run could score {pct_n(s['one_run_range95'][0])} to "
               f"{pct_n(s['one_run_range95'][1])}" for m, s in rows)) + "</desc>"]
    tick = x0
    while tick <= 1.0001:
        out.append(f'<line class="grid" x1="{X(tick):.1f}" x2="{X(tick):.1f}" y1="{top - 8}" y2="{h - 30}"/>')
        out.append(f'<text class="tick" x="{X(tick):.1f}" y="{h - 10}" text-anchor="middle">{pct(tick)}</text>')
        tick = round(tick + 0.1, 10)
    for i, (m, s) in enumerate(rows):
        y = top + row_h * i + row_h / 2 - 6
        meta = feed["models"][m]
        a, b = s["one_run_range95"]
        il, ih = s["interval95"]
        out.append(f'<text class="name" x="{left - 16}" y="{y + 5:.1f}" text-anchor="end">{html.escape(meta["name"])}</text>')
        out.append(f'<rect class="band m-{m}" x="{X(a):.1f}" y="{y - 9:.1f}" width="{max(2, X(b) - X(a)):.1f}" height="18" rx="9"/>')
        out.append(f'<line class="ci m-{m}" x1="{X(il):.1f}" x2="{X(ih):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>')
        for e in (il, ih):
            out.append(f'<line class="ci m-{m}" x1="{X(e):.1f}" x2="{X(e):.1f}" y1="{y - 6:.1f}" y2="{y + 6:.1f}"/>')
        out.append(marker(meta["shape"], X(s["pass_rate"]), y, 6, f"pt m-{m}"))
        out.append(f'<text class="val" x="{w - right + 14}" y="{y + 5:.1f}">{pct(s["pass_rate"])} '
                   f'<tspan class="soft">({pct_n(il)} to {pct_n(ih)})</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


def history_figure(feed: dict) -> str:
    days = feed["days"]
    models = [m for m in feed["models"] if any(m in d["models"] for d in days)]
    pw, ph, gap, w = 190, 150, 20, 820
    cols = 4
    h = ph + 46
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="f2t" class="fig">',
           '<title id="f2t">Daily pass rate with 95% intervals, one panel per model</title>']
    lo = min(d["models"][m]["interval95"][0] for d in days for m in models if m in d["models"])
    y0 = max(0.0, int(lo * 10) / 10 - 0.1)
    for j, m in enumerate(models):
        ox = j * (pw + gap) + 8
        meta = feed["models"][m]
        pts = [(i, d["models"][m]) for i, d in enumerate(days) if m in d["models"]]

        def Y(v):
            return 24 + (ph - 24) * (1 - (v - y0) / (1 - y0))

        def X(i):
            return ox + 30 + (pw - 40) * (0.5 if len(days) == 1 else i / (len(days) - 1))

        out.append(f'<text class="name" x="{ox}" y="14">{html.escape(meta["name"])}</text>')
        for v in (y0, (y0 + 1) / 2, 1.0):
            out.append(f'<line class="grid" x1="{ox + 26}" x2="{ox + pw}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
            out.append(f'<text class="tick" x="{ox + 22}" y="{Y(v) + 4:.1f}" text-anchor="end">{pct_n(v)}</text>')
        if len(pts) > 1:
            path = "M" + "L".join(f"{X(i):.1f} {Y(s['pass_rate']):.1f}" for i, s in pts)
            out.append(f'<path class="trend m-{m}" d="{path}"/>')
        for i, s in pts:
            out.append(f'<line class="ci m-{m}" x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(s["interval95"][0]):.1f}" '
                       f'y2="{Y(s["interval95"][1]):.1f}"/>')
            out.append(marker(meta["shape"], X(i), Y(s["pass_rate"]), 4.5, f"pt m-{m}"))
        first, last = days[0]["date"], days[-1]["date"]
        span = nice_date(first) if first == last else f"{nice_date(first)} to {nice_date(last)}"
        out.append(f'<text class="tick" x="{ox + 26}" y="{ph + 22}">{html.escape(span)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def headline(feed: dict, day: dict) -> str:
    rows = sorted(day["models"].items(), key=lambda kv: -kv[1]["pass_rate"])
    widest = max(rows, key=lambda kv: kv[1]["one_run_range95"][1] - kv[1]["one_run_range95"][0])
    m, s = rows[0]
    wm, ws = widest
    n = feed["runs_per_task_per_day"]
    first = (f"{nice_date(day['date'])}. {feed['models'][m]['name']} passed {pct(s['pass_rate'])} of its "
             f"{s['runs']} runs (95% interval {pct_n(s['interval95'][0])} to {pct_n(s['interval95'][1])}).")
    lo, hi = ws["one_run_range95"]
    if lo == hi:
        return first + f" Every task gave the same result on all {n} runs for every model."
    return (first + f" Run the same {feed['tasks']} tasks once instead of {n} times and "
            f"{feed['models'][wm]['name']} could have scored anywhere from {pct(lo)} to {pct(hi)}.")


def readme_block(feed: dict) -> str:
    day = feed["days"][-1]
    rows = sorted(day["models"].items(), key=lambda kv: -kv[1]["pass_rate"])
    lines = [f"**{headline(feed, day)}**", "",
             "| Model | Pass rate | 95% interval | One run could score | Tasks that flipped |", "| --- | --- | --- | --- | --- |"]
    for m, s in rows:
        lines.append(f"| {feed['models'][m]['name']} | {pct(s['pass_rate'])} | {pct_n(s['interval95'][0])} to "
                     f"{pct_n(s['interval95'][1])} | {pct_n(s['one_run_range95'][0])} to {pct_n(s['one_run_range95'][1])} | "
                     f"{round(s['flip_rate'] * s['tasks'])} of {s['tasks']} |")
    return "\n".join(lines)


def render(feed: dict) -> str:
    day = feed["days"][-1]
    rows = sorted(day["models"].items(), key=lambda kv: -kv[1]["pass_rate"])
    models = feed["models"]

    def change_cell(s):
        c = s.get("change")
        if not c:
            return "first day"
        word = "moved" if c["moved"] else "no clear change"
        return f"{100 * c['diff']:+.0f} points ({word})"

    table = "".join(
        f"<tr><th scope=row>{html.escape(models[m]['name'])}</th><td>{pct(s['pass_rate'])}</td>"
        f"<td>{pct_n(s['interval95'][0])} to {pct_n(s['interval95'][1])}</td>"
        f"<td>{pct_n(s['one_run_range95'][0])} to {pct_n(s['one_run_range95'][1])}</td>"
        f"<td>{'n/a' if s['noise_share'] is None else pct(s['noise_share'])}</td>"
        f"<td>{round(s['flip_rate'] * s['tasks'])} of {s['tasks']}</td><td>{change_cell(s)}</td>"
        f"<td>${s['cost_usd_list_price']:.2f}</td></tr>"
        for m, s in rows
    )
    task_ids = feed["task_ids"]
    task_rows = "".join(
        f"<tr><th scope=row><code>{t}</code></th>"
        + "".join(f"<td>{s['tasks_detail'].get(t, {'passes': 0})['passes']}/{s['tasks_detail'].get(t, {'runs': 0})['runs']}</td>"
                  for _, s in rows)
        + "</tr>"
        for t in task_ids
    )
    heads = "".join(f"<th scope=col>{html.escape(models[m]['name'])}</th>" for m, _ in rows)
    swatches = "\n".join(f".m-{m}{{--c:{c}}}" for m, c in COLOR.items())
    swatches_dark = "\n".join(f".m-{m}{{--c:{c}}}" for m, c in COLOR_DARK.items())
    served = "; ".join(f"{models[m]['name']}: {', '.join(s['served_model_ids'])}" for m, s in rows)
    incomplete = [models[m]["name"] for m, s in rows if not s["complete"]]
    note = (f"<p class=soft>Incomplete today: {', '.join(incomplete)} (fewer than {feed['runs_per_task_per_day']} "
            "runs on some task, from the daily cost cap or provider errors). Their numbers are shown but get no change test.</p>") if incomplete else ""
    outside = [(models[m]["name"], s) for m, s in rows if s["failed_runs_with_refused_outside_write"]]
    if outside:
        note += ("<p class=soft>A harness asymmetry: Claude Code tells Claude models about a working folder and a "
                 "scratch folder of its own, outside the task. "
                 + "; ".join(f"{name} had a write outside the task refused in {s['runs_with_refused_outside_write']} runs, "
                             f"{s['failed_runs_with_refused_outside_write']} of its {s['runs'] - s['passes']} failures"
                             for name, s in outside)
                 + ". The write is refused and costs a turn. Battery v1 keeps the harness fixed, so this stays in "
                 "the numbers; a v2 series would have to take the hint away.</p>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reliability weather</title>
<meta name="description" content="{html.escape(headline(feed, day))}">
<link rel="alternate" type="application/json" href="feed.json" title="reliability weather feed">
<style>
@font-face {{ font-family: "STIX Two Text"; font-style: normal; font-weight: 400 700; font-display: swap; src: url(fonts/STIXTwoText-latin.woff2) format("woff2"); }}
@font-face {{ font-family: "STIX Two Text"; font-style: italic; font-weight: 400 700; font-display: swap; src: url(fonts/STIXTwoText-Italic-latin.woff2) format("woff2"); }}
:root {{ color-scheme: light; --paper:#e8e8e8; --ink:#030303; --gray:rgba(3,3,3,.68); --rule:rgba(3,3,3,.14); --card:#efefee;
  --serif:"STIX Two Text","Times New Roman",Times,serif; --mono:ui-monospace,Menlo,monospace; }}
{swatches}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme: dark; --paper:#121212; --ink:#e2e2df; --gray:rgba(226,226,223,.66); --rule:rgba(226,226,223,.16); --card:#1b1b1a; }}
  :root:not([data-theme="light"]) {{ {swatches_dark.replace(chr(10), ' ')} }} }}
:root[data-theme="dark"] {{ color-scheme: dark; --paper:#121212; --ink:#e2e2df; --gray:rgba(226,226,223,.66); --rule:rgba(226,226,223,.16); --card:#1b1b1a; }}
html {{ background:var(--paper); }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:19px/1.55 var(--serif); }}
main {{ max-width:820px; margin:0 auto; padding:56px 16px 80px; }}
h1 {{ font-size:2.6rem; line-height:1.05; letter-spacing:-0.02em; font-weight:500; margin:0 0 .75rem; }}
h2 {{ font-size:1.35rem; font-weight:500; margin:3.5rem 0 .75rem; }}
p {{ max-width:65ch; margin:0 0 1rem; }}
.lede {{ font-size:1.3rem; line-height:1.45; }}
.soft {{ color:var(--gray); }}
a {{ color:var(--ink); text-decoration-color:color-mix(in srgb, currentColor 32%, transparent); text-underline-offset:.2em; }}
a:hover {{ text-decoration-color:currentColor; }}
figure {{ margin:2rem 0; padding:20px 16px 12px; background:var(--card); border-radius:14px; }}
figcaption {{ font-size:.9rem; color:var(--gray); margin-top:.5rem; max-width:65ch; }}
.fig {{ width:100%; height:auto; display:block; font-family:var(--serif); }}
.fig .grid {{ stroke:var(--rule); stroke-width:1; }}
.fig .tick {{ fill:var(--gray); font-size:13px; }}
.fig .name {{ fill:var(--ink); font-size:15px; }}
.fig .val {{ fill:var(--ink); font-size:15px; }}
.fig .val .soft {{ fill:var(--gray); }}
.fig .band {{ fill:var(--c); opacity:.22; }}
.fig .ci {{ stroke:var(--c); stroke-width:2.5; stroke-linecap:round; }}
.fig .trend {{ stroke:var(--c); stroke-width:1.5; fill:none; opacity:.6; }}
.fig .pt {{ fill:var(--c); stroke:var(--ink); stroke-width:1.2; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:.92rem; font-variant-numeric:tabular-nums; }}
th, td {{ text-align:left; padding:.4rem .6rem .4rem 0; border-bottom:1px solid var(--rule); vertical-align:baseline; }}
thead th {{ font-weight:500; color:var(--gray); }}
code {{ font-family:var(--mono); font-size:.82em; }}
footer {{ margin-top:4rem; font-size:.9rem; color:var(--gray); }}
@media (max-width:600px) {{ body {{ font-size:17px; }} h1 {{ font-size:2rem; }} main {{ padding-top:32px; }} }}
</style>
</head>
<body>
<main>
<h1>Reliability weather</h1>
<p class="lede">{html.escape(headline(feed, day))}</p>
<p>Agent leaderboards report one run per task. This page runs a fixed battery of {feed['tasks']} small coding and
tool-use tasks {feed['runs_per_task_per_day']} times per model every day, through one harness, so the only thing that
changes between rows is the model. Each run is graded by a deterministic check on the files it leaves behind; no model
judges another. The battery, the number of runs and the statistics were <a href="https://github.com/abhaymettu/reliability-weather/blob/main/PREREGISTRATION.md">preregistered</a> before the first run.</p>
{note}
<figure>
{today_figure(feed, day)}
<figcaption>Today, {html.escape(nice_date(day['date']))}. The marker is the pass rate over all runs. The dark line is its
95% interval. The pale band is where one run of the whole battery could have landed, from each task's own pass rate:
the spread a single-run leaderboard hides.</figcaption>
</figure>

<h2>Today in numbers</h2>
<div class="scroll"><table>
<thead><tr><th scope=col>Model</th><th scope=col>Pass rate</th><th scope=col>95% interval</th><th scope=col>One run could score</th><th scope=col>Run-to-run share of variance</th><th scope=col>Tasks that flipped</th><th scope=col>Since last day</th><th scope=col>Cost at list price</th></tr></thead>
<tbody>{table}</tbody></table></div>
<p class="soft">Run-to-run share: of all the variation in single-run outcomes, the part that comes from rerunning the
same model on the same task rather than from tasks differing in difficulty. A task flipped when its
{feed['runs_per_task_per_day']} runs did not all agree. Claude models run on a subscription; their cost is what the
same calls would cost on the API.</p>

<h2>History</h2>
<figure>
{history_figure(feed)}
<figcaption>Pass rate per day with its 95% interval. A day is marked as moved only when the interval for the change
from the previous day excludes zero; with four models a day, expect a false alarm now and then.</figcaption>
</figure>

<h2>Every task, today</h2>
<div class="scroll"><table>
<thead><tr><th scope=col>Task</th>{heads}</tr></thead>
<tbody>{task_rows}</tbody></table></div>

<footer>
<p>Battery {feed['battery']}, sha256 <code>{feed['battery_sha256'][:12]}</code>. Model ids served today: {html.escape(served)}.
Data: <a href="feed.json">feed.json</a> and one file per day under <a href="https://github.com/abhaymettu/reliability-weather/tree/main/docs/days">days/</a>;
every run's transcript, usage and check result are in <a href="https://github.com/abhaymettu/reliability-weather/tree/main/runs">runs/</a>.
Updated {html.escape(feed['generated_utc'].replace('T', ' ').replace('+00:00', ' UTC'))}.
Built by <a href="https://abhaymettu.com">Abhay Mettu</a>, following <a href="https://github.com/abhaymettu/agent-run-reliability">agent-run-reliability</a>.</p>
</footer>
</main>
</body>
</html>
"""
