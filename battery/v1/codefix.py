"""Repair a buggy module. The prompt states the contract; the check runs hidden cases against it."""
import statistics
from bisect import bisect_left
from datetime import date

from weather.battery import compare_cases

TASKS = []


def task(**kw):
    TASKS.append(kw)


task(
    id="fix_median",
    prompt="stats.py has a median(xs) function that gives wrong answers for some inputs. Fix it. median must return "
    "the middle value of the sorted list, the mean of the two middle values for an even-length list, and raise "
    "ValueError for an empty list. It must not modify its argument.",
    setup={"stats.py": "def median(xs):\n    xs.sort()\n    return xs[len(xs) // 2]\n"},
    solution={
        "stats.py": "def median(xs):\n    if not xs:\n        raise ValueError('empty')\n    s = sorted(xs)\n"
        "    n = len(s)\n    m = n // 2\n    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2\n"
    },
    check=lambda w: compare_cases(
        w,
        "from stats import median\nxs = [5, 1, 3]\n_ = median(xs)\n",
        [
            ("median([3, 1, 2])", 2),
            ("median([4, 1, 3, 2])", 2.5),
            ("median([7])", 7),
            ("median([1, 2])", 1.5),
            ("median([-5, 10, 0, 3])", statistics.median([-5, 10, 0, 3])),
            ("median([])", ValueError),
            ("xs", [5, 1, 3]),
        ],
    ),
)

task(
    id="fix_roman",
    prompt="roman.py converts integers to Roman numerals, but some numbers come out wrong. Fix to_roman(n) so it "
    "returns standard Roman numerals (with subtractive forms such as IV, IX, XL, XC, CD, CM) for 1 <= n <= 3999 "
    "and raises ValueError outside that range.",
    setup={
        "roman.py": "PAIRS = [(1000, 'M'), (500, 'D'), (100, 'C'), (50, 'L'), (10, 'X'), (5, 'V'), (1, 'I')]\n\n\n"
        "def to_roman(n):\n    out = ''\n    for value, sym in PAIRS:\n        while n >= value:\n"
        "            out += sym\n            n -= value\n    return out\n"
    },
    solution={
        "roman.py": "PAIRS = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'),"
        " (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]\n\n\n"
        "def to_roman(n):\n    if not 1 <= n <= 3999:\n        raise ValueError(n)\n    out = ''\n"
        "    for value, sym in PAIRS:\n        while n >= value:\n            out += sym\n            n -= value\n"
        "    return out\n"
    },
    check=lambda w: compare_cases(
        w,
        "from roman import to_roman\n",
        [
            ("to_roman(4)", "IV"),
            ("to_roman(9)", "IX"),
            ("to_roman(14)", "XIV"),
            ("to_roman(40)", "XL"),
            ("to_roman(1994)", "MCMXCIV"),
            ("to_roman(2024)", "MMXXIV"),
            ("to_roman(3999)", "MMMCMXCIX"),
            ("to_roman(444)", "CDXLIV"),
            ("to_roman(0)", ValueError),
            ("to_roman(4000)", ValueError),
        ],
    ),
)

task(
    id="fix_dedupe",
    prompt="util.py has dedupe(items), which should remove repeated items while keeping the first occurrence of "
    "each, in the original order. Items may be unhashable (for example lists), and equality is ordinary ==. "
    "It currently loses the order and crashes on lists. Fix it.",
    setup={"util.py": "def dedupe(items):\n    return list(set(items))\n"},
    solution={
        "util.py": "def dedupe(items):\n    out = []\n    for x in items:\n        if x not in out:\n"
        "            out.append(x)\n    return out\n"
    },
    check=lambda w: compare_cases(
        w,
        "from util import dedupe\n",
        [
            ("dedupe([3, 1, 3, 2, 1])", [3, 1, 2]),
            ("dedupe(['b', 'a', 'b'])", ["b", "a"]),
            ("dedupe([[1], [2], [1]])", [[1], [2]]),
            ("dedupe([])", []),
            ("dedupe([1, 1.0, True, 2])", [1, 2]),
        ],
    ),
)

task(
    id="fix_word_count",
    prompt="words.py has top_words(text, k). It should count words case-insensitively, where a word is a maximal "
    "run of ASCII letters and apostrophes (so \"don't\" is one word and \"well-known\" is two), and return the k "
    "most common as a list of (word, count) tuples, sorted by count descending and then alphabetically. Fix it.",
    setup={
        "words.py": "from collections import Counter\n\n\ndef top_words(text, k):\n"
        "    return Counter(text.split()).most_common(k)\n"
    },
    solution={
        "words.py": "import re\nfrom collections import Counter\n\n\ndef top_words(text, k):\n"
        "    c = Counter(re.findall(r\"[a-z']+\", text.lower()))\n"
        "    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:k]\n"
    },
    check=lambda w: compare_cases(
        w,
        "from words import top_words\nT = \"The cat and the hat. THE end; don't stop, don't! A well-known cat.\"\n",
        [
            ("top_words(T, 3)", [["the", 3], ["cat", 2], ["don't", 2]]),
            ("top_words(T, 1)", [["the", 3]]),
            ("top_words('b a c a b', 5)", [["a", 2], ["b", 2], ["c", 1]]),
            ("top_words('', 2)", []),
            ("top_words('x1y2 x', 2)", [["x", 2], ["y", 1]]),
        ],
    ),
)

task(
    id="fix_days_between",
    prompt="dates.py has days_between(a, b), taking two ISO dates as strings (YYYY-MM-DD) and returning the number "
    "of days from a to b (negative if b is earlier). It gets leap years wrong. Fix it.",
    setup={
        "dates.py": "DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n\n\ndef _ordinal(s):\n"
        "    y, m, d = map(int, s.split('-'))\n    return y * 365 + sum(DAYS[: m - 1]) + d\n\n\n"
        "def days_between(a, b):\n    return _ordinal(b) - _ordinal(a)\n"
    },
    solution={
        "dates.py": "from datetime import date\n\n\ndef days_between(a, b):\n"
        "    return (date.fromisoformat(b) - date.fromisoformat(a)).days\n"
    },
    check=lambda w: compare_cases(
        w,
        "from dates import days_between\n",
        [
            ("days_between('2024-02-28', '2024-03-01')", 2),
            ("days_between('2023-02-28', '2023-03-01')", 1),
            ("days_between('1999-12-31', '2000-03-01')", 61),
            ("days_between('1900-02-28', '1900-03-01')", 1),
            ("days_between('2026-11-04', '2020-01-01')", (date(2020, 1, 1) - date(2026, 11, 4)).days),
            ("days_between('2000-01-01', '2000-01-01')", 0),
        ],
    ),
)

task(
    id="fix_bisect",
    prompt="search.py has insertion_point(xs, x) for a sorted list xs. It must return the leftmost index at which "
    "x could be inserted to keep xs sorted (the same contract as bisect.bisect_left), without using the bisect "
    "module. It is wrong at the boundaries and with duplicates. Fix it.",
    setup={
        "search.py": "def insertion_point(xs, x):\n    lo, hi = 0, len(xs) - 1\n    while lo < hi:\n"
        "        mid = (lo + hi) // 2\n        if xs[mid] <= x:\n            lo = mid + 1\n        else:\n"
        "            hi = mid\n    return lo\n"
    },
    solution={
        "search.py": "def insertion_point(xs, x):\n    lo, hi = 0, len(xs)\n    while lo < hi:\n"
        "        mid = (lo + hi) // 2\n        if xs[mid] < x:\n            lo = mid + 1\n        else:\n"
        "            hi = mid\n    return lo\n"
    },
    check=lambda w: compare_cases(
        w,
        "from search import insertion_point\nimport pathlib\nassert 'bisect' not in pathlib.Path('search.py').read_text()\n",
        [(f"insertion_point({xs!r}, {x!r})", bisect_left(xs, x)) for xs, x in [
            ([], 5), ([1], 0), ([1], 1), ([1], 2), ([1, 2, 2, 2, 3], 2), ([1, 3, 5, 7], 8),
            ([1, 3, 5, 7], 4), ([2, 2], 2), ([1, 2, 3, 4, 5, 6], 6), ([0, 10, 20], -1),
        ]],
    ),
)

task(
    id="fix_csv_line",
    prompt="parse.py has split_csv(line), which splits one CSV line into fields. Fields may be wrapped in double "
    "quotes; inside quotes a comma is literal and a doubled quote (\"\") stands for one quote character. The "
    "quotes around a field are not part of its value. It currently breaks on quoted commas. Fix it without "
    "using the csv module.",
    setup={"parse.py": "def split_csv(line):\n    return [f.strip('\"') for f in line.split(',')]\n"},
    solution={
        "parse.py": "def split_csv(line):\n    out, cur, q, i = [], '', False, 0\n    while i < len(line):\n"
        "        c = line[i]\n        if q:\n            if c == '\"' and i + 1 < len(line) and line[i + 1] == '\"':\n"
        "                cur += '\"'\n                i += 1\n            elif c == '\"':\n                q = False\n"
        "            else:\n                cur += c\n        elif c == '\"':\n            q = True\n"
        "        elif c == ',':\n            out.append(cur)\n            cur = ''\n        else:\n            cur += c\n"
        "        i += 1\n    out.append(cur)\n    return out\n"
    },
    check=lambda w: compare_cases(
        w,
        "from parse import split_csv\nimport pathlib\nassert 'csv' not in pathlib.Path('parse.py').read_text().replace('split_csv', '')\n",
        [
            ("split_csv('a,b,c')", ["a", "b", "c"]),
            ("split_csv('\"x, y\",z')", ["x, y", "z"]),
            ("split_csv('\"say \"\"hi\"\"\",2')", ['say "hi"', "2"]),
            ("split_csv(',,')", ["", "", ""]),
            ("split_csv('\"\",a')", ["", "a"]),
            ("split_csv('one')", ["one"]),
        ],
    ),
)

task(
    id="fix_flatten",
    prompt="nest.py has flatten(x), which should turn arbitrarily nested lists and tuples into one flat list, in "
    "order. Strings, bytes and dicts are leaves and must not be split apart. It currently recurses into strings "
    "and misses tuples. Fix it.",
    setup={
        "nest.py": "def flatten(x):\n    out = []\n    for item in x:\n        if hasattr(item, '__iter__'):\n"
        "            out.extend(flatten(item))\n        else:\n            out.append(item)\n    return out\n"
    },
    solution={
        "nest.py": "def flatten(x):\n    out = []\n    for item in x:\n        if isinstance(item, (list, tuple)):\n"
        "            out.extend(flatten(item))\n        else:\n            out.append(item)\n    return out\n"
    },
    check=lambda w: compare_cases(
        w,
        "from nest import flatten\n",
        [
            ("flatten([1, [2, [3, (4, 5)]], 6])", [1, 2, 3, 4, 5, 6]),
            ("flatten(['ab', ['cd']])", ["ab", "cd"]),
            ("flatten([(), [[]], 1])", [1]),
            ("flatten([{'k': 1}, [b'x']])", [{"k": 1}, "b'x'"]),
            ("flatten((1, (2,)))", [1, 2]),
        ],
    ),
)
