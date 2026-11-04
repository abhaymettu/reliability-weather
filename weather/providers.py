"""Chat endpoints. Each provider takes the same message list and returns (reply text, usage record).

A provider object holds one conversation, because Claude through claude -p keeps its history in a session that
later calls resume. The OpenAI-compatible provider sends the whole list every call.
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

CLAUDE_BATCH = os.path.expanduser("~/.local/bin/claude-batch")
CLAUDE_CWD = Path(__file__).resolve().parent.parent / ".state" / "claude-cwd"
DEEPSEEK_AUTH = Path.home() / ".local/share/opencode/auth.json"
DEEPSEEK_BASE = "https://api.deepseek.com"

# List prices per 1M tokens, read from api-docs.deepseek.com/quick_start/pricing on 2026-11-04.
# Peak is 01:00-04:00 and 06:00-10:00 UTC Monday to Friday; every other hour is off-peak at half price.
DEEPSEEK_PEAK_PRICES = {
    "deepseek-flash": {"hit": 0.006, "miss": 0.30, "out": 1.20},
    "deepseek-v4-pro": {"hit": 0.044, "miss": 1.32, "out": 3.96},
}


class InfraError(Exception):
    """The provider failed, not the model: a timeout, a 5xx, a rate limit or an unparseable envelope."""


def deepseek_is_peak(at: datetime) -> bool:
    return at.weekday() < 5 and (1 <= at.hour < 4 or 6 <= at.hour < 10)


def deepseek_cost(model: str, usage: dict, at: datetime) -> float:
    p = DEEPSEEK_PEAK_PRICES[model]
    scale = 1.0 if deepseek_is_peak(at) else 0.5
    hit = usage.get("prompt_cache_hit_tokens", 0)
    miss = usage.get("prompt_cache_miss_tokens", usage.get("prompt_tokens", 0) - hit)
    out = usage.get("completion_tokens", 0)
    return scale * (hit * p["hit"] + miss * p["miss"] + out * p["out"]) / 1e6


@dataclass
class Claude:
    """Claude through his subscription: claude-batch (no tools, no user settings), one session per conversation."""

    model: str
    session_id: str | None = None
    session_cost: float = 0.0

    def send(self, system: str, messages: list[dict]) -> tuple[str, dict]:
        prompt = messages[-1]["content"]
        argv = [CLAUDE_BATCH, "-p", "--model", self.model, "--output-format", "json", "--system-prompt", system]
        if self.session_id:
            argv += ["--resume", self.session_id]
        CLAUDE_CWD.mkdir(parents=True, exist_ok=True)
        try:
            p = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=180, cwd=CLAUDE_CWD)
        except subprocess.TimeoutExpired as e:
            raise InfraError("claude -p timed out after 180 s") from e
        try:
            env = json.loads(p.stdout)
        except json.JSONDecodeError as e:
            raise InfraError(f"claude -p exit {p.returncode}: {(p.stdout + p.stderr)[-300:]}") from e
        if env.get("is_error") or env.get("subtype") != "success":
            raise InfraError(f"claude -p error: {env.get('api_error_status')} {str(env.get('result'))[:300]}")
        self.session_id = env["session_id"]
        # usage is per call, but total_cost_usd and modelUsage add up over the resumed session.
        cumulative = env.get("total_cost_usd") or 0.0
        delta, self.session_cost = cumulative - self.session_cost, cumulative
        record = {
            "usage": env.get("usage"),
            "modelUsage": env.get("modelUsage"),
            "total_cost_usd": env.get("total_cost_usd"),
            "session_id": env["session_id"],
            "duration_ms": env.get("duration_ms"),
            "cost_usd": delta,
        }
        return env.get("result") or "", record


def _deepseek_key() -> str:
    return json.loads(DEEPSEEK_AUTH.read_text())["deepseek"]["key"]


@dataclass
class OpenAICompatible:
    """Any OpenAI-compatible chat endpoint; DeepSeek by default. The key is read from disk at call time."""

    model: str
    base_url: str = DEEPSEEK_BASE
    extra: dict = field(default_factory=dict)

    def send(self, system: str, messages: list[dict]) -> tuple[str, dict]:
        body = {"model": self.model, "messages": [{"role": "system", "content": system}, *messages], **self.extra}
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {_deepseek_key()}"},
        )
        last = ""
        for attempt in range(4):
            at = datetime.now(timezone.utc)
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    env = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}: {e.read()[:300]!r}"
                if e.code < 500 and e.code != 429:
                    raise InfraError(last) from e
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = repr(e)
            time.sleep(5 * 2**attempt)
        else:
            raise InfraError(last)
        usage = env.get("usage") or {}
        record = {
            "usage": usage,
            "model": env.get("model"),
            "system_fingerprint": env.get("system_fingerprint"),
            "at_utc": at.isoformat(timespec="seconds"),
            "peak": deepseek_is_peak(at),
            "cost_usd": deepseek_cost(self.model, usage, at),
        }
        return env["choices"][0]["message"].get("content") or "", record


def run_cost(calls: list[dict]) -> float:
    """List-price cost of one run from its call records. Claude records carry a session total, so the last one is the
    run's cost; DeepSeek records are per call. Receipts written before the per-call fix only have the totals."""
    if calls and "total_cost_usd" in calls[-1]:
        return calls[-1]["total_cost_usd"] or 0.0
    return sum(c.get("cost_usd", 0.0) for c in calls)


def make(name: str):
    """Model names in the battery config map to providers here."""
    if name in ("sonnet", "haiku"):
        return Claude(name)
    if name in DEEPSEEK_PEAK_PRICES:
        return OpenAICompatible(name)
    raise ValueError(f"unknown model {name}")
