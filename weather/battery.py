"""Load a versioned task battery. A task is data plus a deterministic check; checks never call a model."""
import hashlib
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .sandbox import run_python

ROOT = Path(__file__).resolve().parent.parent / "battery"
CATEGORIES = ("codefix", "implement", "data", "chore")


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    prompt: str
    setup: dict[str, str]
    solution: dict[str, str]
    check: Callable[[Path], tuple[bool, str]]

    def materialize(self, work: Path, with_solution: bool = False) -> None:
        for rel, text in {**self.setup, **(self.solution if with_solution else {})}.items():
            p = work / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)


def load(version: str) -> list[Task]:
    tasks = []
    for cat in CATEGORIES:
        mod = importlib.import_module(f"battery.{version}.{cat}")
        for t in mod.TASKS:
            tasks.append(Task(category=cat, **t))
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task id"
    return tasks


def digest(version: str) -> str:
    """sha256 over the battery's source files, in name order. A receipt carries it so a changed battery is visible."""
    h = hashlib.sha256()
    for p in sorted((ROOT / version).glob("*.py")):
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def _norm(v):
    return json.loads(json.dumps(v, default=repr))


def evaluate(work: Path, preamble: str, exprs: list[str], timeout: float = 20) -> list | str:
    """Evaluate each expression in the sandbox after `preamble`; returns [["ok", value] | ["err", ExcName]] or an error string."""
    script = (
        "import json, sys\nsys.path.insert(0, '.')\n"
        + preamble
        + "\n_out = []\n"
        + f"for _e in {exprs!r}:\n"
        + "    try:\n        _out.append(['ok', eval(_e)])\n"
        + "    except Exception as _x:\n        _out.append(['err', type(_x).__name__])\n"
        + "print('@@RESULT@@' + json.dumps(_out, default=repr))\n"
    )
    code, out = run_python(work, ["-c", script], timeout=timeout)
    marker = out.rfind("@@RESULT@@")
    if marker < 0:
        return f"checker script failed (exit {code}): {out[-300:]}"
    return json.loads(out[marker + len("@@RESULT@@") :].splitlines()[0])


def compare_cases(work: Path, preamble: str, cases: list[tuple[str, object]]) -> tuple[bool, str]:
    """cases: (expression, expected). An expected value of the exception class means that exception must be raised."""
    got = evaluate(work, preamble, [e for e, _ in cases])
    if isinstance(got, str):
        return False, got
    for (expr, want), (kind, val) in zip(cases, got):
        if isinstance(want, type) and issubclass(want, BaseException):
            if kind != "err" or val != want.__name__:
                return False, f"{expr}: expected {want.__name__}, got {kind} {val!r}"
        elif kind != "ok" or val != _norm(want):
            return False, f"{expr}: expected {_norm(want)!r}, got {kind} {val!r}"
    return True, f"{len(cases)} cases pass"


def files_equal(work: Path, rel: str, want: str) -> tuple[bool, str]:
    p = work / rel
    if not p.is_file():
        return False, f"{rel} missing"
    got = p.read_text()
    if got.rstrip("\n") != want.rstrip("\n"):
        return False, f"{rel} differs from expected"
    return True, f"{rel} matches"
