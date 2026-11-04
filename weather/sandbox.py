"""Run Python written by a model under macOS sandbox-exec: no network, writes only inside the work directory."""
import os
import subprocess
from pathlib import Path

PYTHON = "/opt/homebrew/bin/python3"
TIMEOUT_S = 10
OUTPUT_CAP = 4000

PROFILE = """(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "{work}") (literal "/dev/null") (literal "/dev/tty"))
(deny file-read* (subpath "/Users"))
(allow file-read* (subpath "{work}"))
"""


def run_python(work: Path, args: list[str], stdin: str = "", timeout: float = TIMEOUT_S) -> tuple[int, str]:
    """Run `python3 <args>` in `work`. Returns (exit code, combined stdout and stderr, capped). 124 means timeout."""
    work = Path(os.path.realpath(work))
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "TMPDIR": str(work),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "LANG": "en_US.UTF-8",
    }
    argv = ["/usr/bin/sandbox-exec", "-p", PROFILE.format(work=work), PYTHON, *args]
    try:
        p = subprocess.run(argv, cwd=work, env=env, input=stdin, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        return 124, (out + f"\n[timed out after {timeout:g} s]")[-OUTPUT_CAP:]
    out = p.stdout + p.stderr
    if len(out) > OUTPUT_CAP:
        out = out[: OUTPUT_CAP // 2] + "\n[... output truncated ...]\n" + out[-OUTPUT_CAP // 2 :]
    return p.returncode, out
