"""Multi-file changes to a small project: rename, split, untangle, add a CLI, bump, make tests green."""
import hashlib

from weather.battery import compare_cases, files_equal
from weather.sandbox import run_python

TASKS = []


def task(**kw):
    TASKS.append(kw)


def _all(*checks):
    for ok, why in checks:
        if not ok:
            return False, why
    return True, "all checks pass"


def _no_text(work, needle, glob="**/*.py"):
    hits = [str(p.relative_to(work)) for p in work.glob(glob) if needle in p.read_text()]
    return (not hits), (f"'{needle}' still in {hits}" if hits else f"no '{needle}'")


_SHOP = {
    "shop/__init__.py": "",
    "shop/pricing.py": "def calc(items, tax=0.0):\n    \"\"\"Total of (price, qty) pairs plus tax.\"\"\"\n"
    "    sub = sum(p * q for p, q in items)\n    return round(sub * (1 + tax), 2)\n",
    "shop/cart.py": "from shop.pricing import calc\n\n\nclass Cart:\n    def __init__(self):\n        self.items = []\n\n"
    "    def add(self, price, qty=1):\n        self.items.append((price, qty))\n\n    def total(self, tax=0.0):\n"
    "        return calc(self.items, tax)\n",
    "shop/report.py": "from shop import pricing\n\n\ndef line(items):\n    return f'total={pricing.calc(items)}'\n",
    "main.py": "from shop.cart import Cart\n\nc = Cart()\nc.add(2.5, 2)\nc.add(1.0)\nprint(c.total(0.1))\n",
}

task(
    id="chore_rename",
    prompt="Rename the function calc in shop/pricing.py to compute_total, and update every use of it across the "
    "project so everything still works. Do not leave an alias under the old name.",
    setup=_SHOP,
    solution={
        **{k: v.replace("calc", "compute_total") for k, v in _SHOP.items() if "calc" in v},
    },
    check=lambda w: _all(
        _no_text(w, "calc"),
        compare_cases(
            w,
            "from shop.pricing import compute_total\nfrom shop.cart import Cart\nfrom shop.report import line\n"
            "c = Cart()\nc.add(3.0, 3)\n",
            [("compute_total([(1.0, 2)], 0.5)", 3.0), ("c.total()", 9.0), ("line([(2.0, 2)])", "total=4.0")],
        ),
    ),
)

_GEOM = (
    "import math\n\n\nclass Vec:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\n"
    "    def __add__(self, o):\n        return Vec(self.x + o.x, self.y + o.y)\n\n    def norm(self):\n"
    "        return math.hypot(self.x, self.y)\n\n\ndef area(points):\n    \"\"\"Shoelace area of a polygon given as Vecs.\"\"\"\n"
    "    s = 0.0\n    for a, b in zip(points, points[1:] + points[:1]):\n        s += a.x * b.y - b.x * a.y\n"
    "    return abs(s) / 2\n\n\ndef centroid(points):\n    n = len(points)\n"
    "    return Vec(sum(p.x for p in points) / n, sum(p.y for p in points) / n)\n"
)
_VEC_ONLY = (
    "import math\n\n\nclass Vec:\n    def __init__(self, x, y):\n        self.x, self.y = x, y\n\n"
    "    def __add__(self, o):\n        return Vec(self.x + o.x, self.y + o.y)\n\n    def norm(self):\n"
    "        return math.hypot(self.x, self.y)\n"
)


def _check_split(work):
    vec = work / "geom" / "vec.py"
    if not vec.is_file() or "class Vec" not in vec.read_text():
        return False, "geom/vec.py does not define Vec"
    if "class Vec" in (work / "geom" / "shapes.py").read_text():
        return False, "geom/shapes.py still defines Vec"
    return compare_cases(
        work,
        "from geom.shapes import Vec as V1, area\nfrom geom.vec import Vec as V2\n"
        "sq = [V2(0, 0), V2(2, 0), V2(2, 2), V2(0, 2)]\n",
        [("V1 is V2", True), ("area(sq)", 4.0), ("(V1(3, 4) + V2(0, 0)).norm()", 5.0)],
    )


task(
    id="chore_split_module",
    prompt="Move the Vec class out of geom/shapes.py into a new module geom/vec.py. Existing code that does "
    "'from geom.shapes import Vec' must keep working and get the same class.",
    setup={"geom/__init__.py": "", "geom/shapes.py": _GEOM},
    solution={"geom/vec.py": _VEC_ONLY,
              "geom/shapes.py": "from geom.vec import Vec\n" + _GEOM[_GEOM.index("\n\ndef area"):]},
    check=_check_split,
)

task(
    id="chore_circular_import",
    prompt="Running 'python3 app.py' fails with an ImportError caused by a circular import between pkg/models.py "
    "and pkg/validate.py. Fix the package so app.py runs and prints its result, without changing app.py and "
    "without changing what the functions return.",
    setup={
        "pkg/__init__.py": "",
        "pkg/models.py": "from pkg.validate import check_name\n\n\nclass User:\n    def __init__(self, name):\n"
        "        check_name(name)\n        self.name = name\n\n\nDEFAULT_NAME = 'guest'\n",
        "pkg/validate.py": "from pkg.models import DEFAULT_NAME\n\n\ndef check_name(name):\n"
        "    if not name or name == DEFAULT_NAME.upper():\n        raise ValueError(name)\n    return True\n",
        "app.py": "from pkg.models import User\n\nprint(User('ada').name)\n",
    },
    solution={
        "pkg/validate.py": "def check_name(name):\n    from pkg.models import DEFAULT_NAME\n\n"
        "    if not name or name == DEFAULT_NAME.upper():\n        raise ValueError(name)\n    return True\n",
    },
    check=lambda w: _all(
        files_equal(w, "app.py", "from pkg.models import User\n\nprint(User('ada').name)\n"),
        (lambda r: (r[0] == 0 and r[1].strip() == "ada", f"app.py: exit {r[0]} {r[1][-200:]!r}"))(
            run_python(w, ["app.py"])),
        compare_cases(
            w,
            "import pkg.validate\nfrom pkg.models import User\n",
            [("pkg.validate.check_name('x')", True), ("pkg.validate.check_name('GUEST')", ValueError),
             ("User('')", ValueError)],
        ),
    ),
)

_TOOL = "def transform(text, upper=False, reverse=False):\n    if upper:\n        text = text.upper()\n" \
        "    if reverse:\n        text = text[::-1]\n    return text\n"


def _cli(work, args, want_code, want_out):
    code, out = run_python(work, ["tool.py", *args])
    ok = code == want_code and (want_out is None or out.strip() == want_out)
    return ok, f"tool.py {args}: exit {code}, output {out.strip()[-120:]!r}"


task(
    id="chore_add_cli",
    prompt="tool.py defines transform(). Make 'python3 tool.py [--upper] [--reverse] TEXT...' work: it joins the "
    "TEXT arguments with single spaces, applies transform with the given flags, prints the result and exits 0. "
    "With no TEXT it must exit with status 2 (argparse's usage error). Importing tool must not run the CLI.",
    setup={"tool.py": _TOOL},
    solution={"tool.py": _TOOL + "\n\nif __name__ == '__main__':\n    import argparse\n\n"
              "    p = argparse.ArgumentParser()\n    p.add_argument('--upper', action='store_true')\n"
              "    p.add_argument('--reverse', action='store_true')\n    p.add_argument('text', nargs='+')\n"
              "    a = p.parse_args()\n    print(transform(' '.join(a.text), a.upper, a.reverse))\n"},
    check=lambda w: _all(
        _cli(w, ["hello", "world"], 0, "hello world"),
        _cli(w, ["--upper", "abc"], 0, "ABC"),
        _cli(w, ["--reverse", "--upper", "ab", "c"], 0, "C BA"),
        _cli(w, [], 2, None),
        compare_cases(w, "import tool\n", [("tool.transform('x', upper=True)", "X")]),
    ),
)

_CHANGELOG = "# Changelog\n\n## 1.4.2 - 2026-09-30\n\n- Fix a crash on empty input.\n\n## 1.4.1 - 2026-08-02\n\n- First public release.\n"
_CHANGELOG_NEW = "# Changelog\n\n## 1.5.0 - 2026-11-04\n\n- Add the --json flag.\n\n" + _CHANGELOG[len("# Changelog\n\n"):]

task(
    id="chore_version_bump",
    prompt="Release version 1.5.0 of this project. The version string appears in pyproject.toml, "
    "src/fmt/__init__.py and README.md; update all three (and nothing else that only happens to look like a "
    "version). Add a new top entry to CHANGELOG.md in the same format as the existing ones, dated 2026-11-04, "
    "with the single bullet '- Add the --json flag.'",
    setup={
        "pyproject.toml": "[project]\nname = \"fmt\"\nversion = \"1.4.2\"\nrequires-python = \">=3.10\"\n"
        "dependencies = [\"click>=1.4.2\"]\n",
        "src/fmt/__init__.py": "__version__ = \"1.4.2\"\nMIN_SCHEMA = \"1.4.2\"  # schema version, not the package\n",
        "README.md": "# fmt\n\nCurrent version: 1.4.2\n\nRequires click 1.4.2 or newer.\n",
        "CHANGELOG.md": _CHANGELOG,
    },
    solution={
        "pyproject.toml": "[project]\nname = \"fmt\"\nversion = \"1.5.0\"\nrequires-python = \">=3.10\"\n"
        "dependencies = [\"click>=1.4.2\"]\n",
        "src/fmt/__init__.py": "__version__ = \"1.5.0\"\nMIN_SCHEMA = \"1.4.2\"  # schema version, not the package\n",
        "README.md": "# fmt\n\nCurrent version: 1.5.0\n\nRequires click 1.4.2 or newer.\n",
        "CHANGELOG.md": _CHANGELOG_NEW,
    },
    check=lambda w: _all(
        files_equal(w, "pyproject.toml", "[project]\nname = \"fmt\"\nversion = \"1.5.0\"\nrequires-python = "
                    "\">=3.10\"\ndependencies = [\"click>=1.4.2\"]\n"),
        files_equal(w, "src/fmt/__init__.py",
                    "__version__ = \"1.5.0\"\nMIN_SCHEMA = \"1.4.2\"  # schema version, not the package\n"),
        files_equal(w, "README.md", "# fmt\n\nCurrent version: 1.5.0\n\nRequires click 1.4.2 or newer.\n"),
        files_equal(w, "CHANGELOG.md", _CHANGELOG_NEW),
    ),
)

_TESTS = (
    "import unittest\n\nfrom money import Money\n\n\nclass T(unittest.TestCase):\n"
    "    def test_add(self):\n        self.assertEqual(Money(150) + Money(275), Money(425))\n\n"
    "    def test_str(self):\n        self.assertEqual(str(Money(5)), '$0.05')\n"
    "        self.assertEqual(str(Money(123456)), '$1,234.56')\n        self.assertEqual(str(Money(-250)), '-$2.50')\n\n"
    "    def test_split(self):\n        self.assertEqual(Money(100).split(3), [Money(34), Money(33), Money(33)])\n"
    "        self.assertEqual(sum((m.cents for m in Money(7).split(4))), 7)\n\n\n"
    "if __name__ == '__main__':\n    unittest.main()\n"
)
_TESTS_SHA = hashlib.sha256(_TESTS.encode()).hexdigest()
_MONEY_BUGGY = (
    "class Money:\n    def __init__(self, cents):\n        self.cents = cents\n\n    def __add__(self, o):\n"
    "        return Money(self.cents + o.cents)\n\n    def __eq__(self, o):\n"
    "        return isinstance(o, Money) and self.cents == o.cents\n\n    def __repr__(self):\n"
    "        return f'Money({self.cents})'\n\n    def __str__(self):\n        return f'${self.cents / 100:,.2f}'\n\n"
    "    def split(self, n):\n        share = self.cents // n\n        return [Money(share) for _ in range(n)]\n"
)
_MONEY_FIXED = _MONEY_BUGGY.replace(
    "        return f'${self.cents / 100:,.2f}'\n",
    "        sign = '-' if self.cents < 0 else ''\n        return f'{sign}${abs(self.cents) / 100:,.2f}'\n",
).replace(
    "        share = self.cents // n\n        return [Money(share) for _ in range(n)]\n",
    "        share, extra = divmod(self.cents, n)\n        return [Money(share + (i < extra)) for i in range(n)]\n",
)


def _check_green(work):
    t = work / "test_money.py"
    if not t.is_file() or hashlib.sha256(t.read_bytes()).hexdigest() != _TESTS_SHA:
        return False, "test_money.py was changed"
    code, out = run_python(work, ["-m", "unittest", "-q", "test_money"])
    if code != 0:
        return False, f"unit tests fail: {out[-200:]!r}"
    return compare_cases(
        work,
        "from money import Money\n",
        [("str(Money(-5))", "-$0.05"), ("[m.cents for m in Money(10).split(3)]", [4, 3, 3]),
         ("str(Money(100000000))", "$1,000,000.00"), ("[m.cents for m in Money(2).split(5)]", [1, 1, 0, 0, 0])],
    )


task(
    id="chore_tests_green",
    prompt="'python3 -m unittest test_money' fails. Fix money.py so the tests pass, without editing "
    "test_money.py. Keep the behaviour general: the tests show the intended contract, not special cases.",
    setup={"money.py": _MONEY_BUGGY, "test_money.py": _TESTS},
    solution={"money.py": _MONEY_FIXED},
    check=_check_green,
)
