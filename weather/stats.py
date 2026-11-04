"""The preregistered statistics (PREREGISTRATION.md section 4). Pure functions of per-task pass counts.

counts: {task_id: (passes, runs)} for one model on one day.
"""
import hashlib
import math
import random

BOOT = 5000


def _rng(*keys: str) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(keys).encode()).hexdigest()[:16], 16))


def _pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    i = q * (len(s) - 1)
    lo, hi = math.floor(i), math.ceil(i)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def pass_rate(counts: dict) -> float:
    return sum(k / n for k, n in counts.values()) / len(counts)


Z = 1.959963984540054


def wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson score 95% interval for k passes in n runs."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    centre = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def pooled(counts: dict) -> tuple[int, int]:
    return sum(k for k, _ in counts.values()), sum(n for _, n in counts.values())


def one_run_range(counts: dict) -> tuple[float, float]:
    """2.5th and 97.5th percentiles of the score one run of the whole battery would get, each task passing with its
    observed rate. Exact Poisson-binomial distribution, no simulation."""
    dist = [1.0]
    for k, n in counts.values():
        p = k / n
        nxt = [0.0] * (len(dist) + 1)
        for s, w in enumerate(dist):
            nxt[s] += w * (1 - p)
            nxt[s + 1] += w * p
        dist = nxt
    t = len(counts)

    def quantile(q):
        acc = 0.0
        for s, w in enumerate(dist):
            acc += w
            if acc >= q - 1e-12:
                return s / t
        return 1.0

    return quantile(0.025), quantile(0.975)


def task_bootstrap(counts: dict, *seed: str) -> tuple[float, float]:
    """Secondary interval: resample tasks, then runs within each resampled task (generalizes to similar tasks)."""
    rng = _rng("bootstrap", *seed)
    rows = list(counts.values())
    out = []
    for _ in range(BOOT):
        tot = 0.0
        for _ in rows:
            k, n = rows[rng.randrange(len(rows))]
            tot += sum(rng.random() < k / n for _ in range(n)) / n
        out.append(tot / len(rows))
    return _pct(out, 0.025), _pct(out, 0.975)


def noise_share(counts: dict) -> float | None:
    """Share of the variance in single-run outcomes that is run-to-run (within task) rather than between tasks.

    Within: mean over tasks of the unbiased Bernoulli variance k(n-k)/(n(n-1)). Total: the unbiased variance of all
    outcomes pooled. Undefined when every outcome is the same or a task has fewer than two runs.
    """
    if any(n < 2 for _, n in counts.values()):
        return None
    within = sum(k * (n - k) / (n * (n - 1)) for k, n in counts.values()) / len(counts)
    big_k = sum(k for k, _ in counts.values())
    big_n = sum(n for _, n in counts.values())
    total = big_k * (big_n - big_k) / (big_n * (big_n - 1))
    return None if total == 0 else min(1.0, within / total)


def flip_rate(counts: dict) -> float:
    """Share of tasks whose runs disagree (some pass, some fail)."""
    return sum(0 < k < n for k, n in counts.values()) / len(counts)


def summarize(counts: dict, label: str, model: str) -> dict:
    k, n = pooled(counts)
    return {
        "tasks": len(counts),
        "runs": n,
        "passes": k,
        "pass_rate": pass_rate(counts),
        "interval95": list(wilson(k, n)),
        "task_bootstrap95": list(task_bootstrap(counts, label, model)),
        "one_run_range95": list(one_run_range(counts)),
        "noise_share": noise_share(counts),
        "flip_rate": flip_rate(counts),
    }


def change(today: dict, before: dict) -> dict:
    """Newcombe hybrid score 95% interval for today's pass rate minus the earlier day's; moved when it excludes 0."""
    k1, n1 = pooled(today)
    k2, n2 = pooled(before)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return {"diff": d, "interval95": [lo, hi], "moved": lo > 0 or hi < 0}
