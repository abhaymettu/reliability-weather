"""The agent loop every model runs: one JSON action per turn against a work directory, a fixed turn budget."""
import json
import re
from pathlib import Path

from .sandbox import OUTPUT_CAP, run_python

MAX_TURNS = 4

SYSTEM = """You are a careful software engineer working alone in a project directory.
Each turn, reply with exactly one JSON object and nothing else. The available actions are:
{"action": "list", "path": "."}                              list files under a directory, recursively
{"action": "read", "path": "FILE"}                           read a text file
{"action": "write", "path": "FILE", "content": "TEXT"}       create or overwrite a file with the full new content
{"action": "run", "args": ["script.py", "arg1"]}             run python3 with these arguments in the project directory (10 s limit, no network)
{"action": "finish"}                                         stop; your work is graded on the files as they are now
You see the result of each action before your next turn. You have a limited number of turns; when they run out,
the files are graded as they are. Paths are relative to the project directory."""


def parse_action(text: str) -> dict | None:
    """The first JSON object in the reply that has an "action" key, tolerating code fences and prose around it."""
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text, m.start())
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "action" in obj:
            return obj
    return None


def _inside(work: Path, rel) -> Path | None:
    if not isinstance(rel, str):
        return None
    p = (work / rel).resolve()
    return p if p == work or work in p.parents else None


def act(work: Path, action: dict) -> str:
    kind = action.get("action")
    if kind == "list":
        root = _inside(work, action.get("path", "."))
        if root is None or not root.is_dir():
            return "error: not a directory inside the project"
        files = sorted(str(p.relative_to(work)) for p in root.rglob("*") if p.is_file())
        return "\n".join(files) or "(empty)"
    if kind == "read":
        p = _inside(work, action.get("path"))
        if p is None or not p.is_file():
            return "error: no such file inside the project"
        text = p.read_text(errors="replace")
        return text if len(text) <= OUTPUT_CAP * 3 else text[: OUTPUT_CAP * 3] + "\n[... file truncated ...]"
    if kind == "write":
        p = _inside(work, action.get("path"))
        content = action.get("content")
        if p is None or p == work or not isinstance(content, str):
            return "error: write needs a path inside the project and string content"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"wrote {p.relative_to(work)} ({len(content)} chars)"
    if kind == "run":
        args = action.get("args")
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args) or not args:
            return 'error: run needs "args", a non-empty list of strings passed to python3'
        if args[0] in ("python3", "python"):
            args = args[1:]
        code, out = run_python(work, args)
        return f"exit code {code}\n{out}"
    return "error: unknown action; use list, read, write, run or finish"


def run_episode(provider, prompt: str, work: Path, max_turns: int = MAX_TURNS) -> dict:
    """Drive one conversation to a finish or the turn limit. Raises providers.InfraError on provider failure."""
    work = work.resolve()
    messages = [{"role": "user", "content": f"{prompt}\n\nYou have {max_turns} turns."}]
    turns, calls = [], []
    ended = "turn_limit"
    for t in range(1, max_turns + 1):
        reply, usage = provider.send(SYSTEM, messages)
        calls.append(usage)
        messages.append({"role": "assistant", "content": reply})
        action = parse_action(reply)
        if action is None:
            result = 'error: reply was not a JSON object with an "action" key'
        elif action.get("action") == "finish":
            turns.append({"turn": t, "reply": reply, "result": None})
            ended = "finish"
            break
        else:
            result = act(work, action)
        turns.append({"turn": t, "reply": reply, "result": result})
        left = max_turns - t
        messages.append({"role": "user", "content": f"Result:\n{result}\n\nTurns left: {left}."})
    return {"ended": ended, "turns": turns, "calls": calls}
