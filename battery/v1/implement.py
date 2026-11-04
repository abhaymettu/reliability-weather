"""Write a module from a stated contract. The check runs hidden cases, including the edges the contract names."""
from weather.battery import compare_cases

TASKS = []


def task(**kw):
    TASKS.append(kw)


task(
    id="impl_rle",
    prompt="Create rle.py with encode(s) and decode(s). encode turns runs of the same character into the character "
    "followed by the run length, omitting the length when it is 1: encode('aaabcc') == 'a3bc2'. Input to encode "
    "contains only letters. decode is the exact inverse and must handle run lengths of more than one digit.",
    setup={},
    solution={
        "rle.py": "import re\nfrom itertools import groupby\n\n\ndef encode(s):\n"
        "    return ''.join(c + (str(n) if (n := len(list(g))) > 1 else '') for c, g in groupby(s))\n\n\n"
        "def decode(s):\n    return ''.join(c * int(n or 1) for c, n in re.findall(r'([A-Za-z])(\\d*)', s))\n"
    },
    check=lambda w: compare_cases(
        w,
        "from rle import encode, decode\n",
        [
            ("encode('aaabcc')", "a3bc2"),
            ("encode('')", ""),
            ("encode('abc')", "abc"),
            ("encode('z' * 12 + 'Zz')", "z12Zz"),
            ("decode('a3bc2')", "aaabcc"),
            ("decode('x10y')", "x" * 10 + "y"),
            ("decode(encode('qqqqqqqqqqqqqqqqwwe'))", "qqqqqqqqqqqqqqqqwwe"),
        ],
    ),
)

task(
    id="impl_semver",
    prompt="Create semver.py with sort_versions(vs), which returns the list of semantic version strings sorted by "
    "SemVer 2.0.0 precedence, lowest first. Versions look like MAJOR.MINOR.PATCH with an optional pre-release "
    "after a hyphen (1.0.0-alpha.1) and optional build metadata after a plus (1.0.0+build.5), which is ignored for "
    "ordering. Rules: numeric parts compare as integers; a pre-release version is lower than the same version "
    "without one; pre-release identifiers compare left to right, numeric identifiers as integers and lower than "
    "alphanumeric ones, alphanumeric ones in ASCII order, and a shorter list is lower when all shared ones are "
    "equal. Versions that tie keep their input order.",
    setup={},
    solution={
        "semver.py": "def _key(v):\n    core = v.split('+')[0]\n    main, _, pre = core.partition('-')\n"
        "    nums = tuple(int(x) for x in main.split('.'))\n    if not pre:\n        return nums, (1,)\n"
        "    ids = tuple((0, int(p), '') if p.isdigit() else (1, 0, p) for p in pre.split('.'))\n"
        "    return nums, (0, ids)\n\n\ndef sort_versions(vs):\n    return sorted(vs, key=_key)\n"
    },
    check=lambda w: compare_cases(
        w,
        "from semver import sort_versions\n",
        [
            (
                "sort_versions(['1.0.0', '1.0.0-rc.1', '1.0.0-alpha', '1.0.0-alpha.beta', '1.0.0-beta.11', "
                "'1.0.0-beta.2', '1.0.0-beta', '1.0.0-alpha.1'])",
                ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
                 "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"],
            ),
            ("sort_versions(['10.0.0', '9.9.9', '1.10.0', '1.9.0'])", ["1.9.0", "1.10.0", "9.9.9", "10.0.0"]),
            ("sort_versions(['1.0.0+b', '1.0.0+a', '0.9.0'])", ["0.9.0", "1.0.0+b", "1.0.0+a"]),
            ("sort_versions(['2.0.0-1', '2.0.0-a', '2.0.0-0'])", ["2.0.0-0", "2.0.0-1", "2.0.0-a"]),
            ("sort_versions(['1.0.0-B', '1.0.0-a'])", ["1.0.0-B", "1.0.0-a"]),
        ],
    ),
)

task(
    id="impl_merge_intervals",
    prompt="Create intervals.py with merge(intervals): given a list of [start, end] pairs of integers (start <= "
    "end, in any order), return the merged list of disjoint intervals sorted by start. Intervals that overlap or "
    "touch ([1, 3] and [3, 5]) merge. Do not modify the input.",
    setup={},
    solution={
        "intervals.py": "def merge(intervals):\n    out = []\n    for s, e in sorted(intervals):\n"
        "        if out and s <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n        else:\n"
        "            out.append([s, e])\n    return out\n"
    },
    check=lambda w: compare_cases(
        w,
        "from intervals import merge\nI = [[5, 6], [1, 3]]\n_ = merge(I)\n",
        [
            ("merge([[1, 3], [2, 6], [8, 10], [15, 18]])", [[1, 6], [8, 10], [15, 18]]),
            ("merge([[1, 3], [3, 5]])", [[1, 5]]),
            ("merge([[4, 7], [1, 2], [2, 3]])", [[1, 3], [4, 7]]),
            ("merge([])", []),
            ("merge([[1, 10], [2, 3], [4, 5]])", [[1, 10]]),
            ("merge([[0, 0], [0, 0]])", [[0, 0]]),
            ("I", [[5, 6], [1, 3]]),
        ],
    ),
)

task(
    id="impl_slugify",
    prompt="Create slug.py with slugify(title). Rules, in order: lowercase; replace each '&' with ' and '; drop "
    "every character that is not an ASCII letter, digit, space or hyphen; turn each run of spaces and hyphens "
    "into one hyphen; strip hyphens from both ends; if the result is longer than 40 characters, cut it to 40 and "
    "then strip any trailing hyphen.",
    setup={},
    solution={
        "slug.py": "import re\n\n\ndef slugify(title):\n    s = title.lower().replace('&', ' and ')\n"
        "    s = re.sub(r'[^a-z0-9 -]', '', s)\n    s = re.sub(r'[ -]+', '-', s).strip('-')\n"
        "    return s[:40].rstrip('-') if len(s) > 40 else s\n"
    },
    check=lambda w: compare_cases(
        w,
        "from slug import slugify\n",
        [
            ("slugify('Hello, World!')", "hello-world"),
            ("slugify('Salt & Pepper')", "salt-and-pepper"),
            ("slugify('  --Already--slugged--  ')", "already-slugged"),
            ("slugify('Café déjà vu')", "caf-dj-vu"),
            ("slugify('a' * 39 + ' bc')", "a" * 39),
            ("slugify('x' * 45)", "x" * 40),
            ("slugify('!!!')", ""),
        ],
    ),
)

task(
    id="impl_lru",
    prompt="Create lru.py with a class LRUCache(capacity). get(key) returns the value or None and counts as a use; "
    "put(key, value) inserts or updates and counts as a use; when an insert would exceed capacity, the least "
    "recently used key is evicted first. len(cache) gives the number of keys. capacity is at least 1.",
    setup={},
    solution={
        "lru.py": "from collections import OrderedDict\n\n\nclass LRUCache:\n    def __init__(self, capacity):\n"
        "        self.cap = capacity\n        self.d = OrderedDict()\n\n    def get(self, key):\n"
        "        if key not in self.d:\n            return None\n        self.d.move_to_end(key)\n"
        "        return self.d[key]\n\n    def put(self, key, value):\n        self.d[key] = value\n"
        "        self.d.move_to_end(key)\n        if len(self.d) > self.cap:\n            self.d.popitem(last=False)\n\n"
        "    def __len__(self):\n        return len(self.d)\n"
    },
    check=lambda w: compare_cases(
        w,
        "from lru import LRUCache\nc = LRUCache(2)\nc.put('a', 1)\nc.put('b', 2)\nr1 = c.get('a')\nc.put('c', 3)\n"
        "r2 = c.get('b')\nc.put('a', 10)\nc.put('d', 4)\nr3 = (c.get('a'), c.get('c'), c.get('d'), len(c))\n"
        "one = LRUCache(1)\none.put(1, 1)\none.put(2, 2)\nr4 = (one.get(1), one.get(2), len(one))\n",
        [("r1", 1), ("r2", None), ("r3", [10, None, 4, 2]), ("r4", [None, 2, 1])],
    ),
)

task(
    id="impl_duration",
    prompt="Create duration.py with parse_duration(s), which turns strings like '1h30m', '45s', '2h5s' or '1d2h' "
    "into a number of seconds (an int). Units are d, h, m and s; each unit appears at most once and in that order; "
    "each amount is a non-negative integer. Surrounding whitespace is allowed. Anything else, including an empty "
    "string, a repeated unit, units out of order or a bare number, raises ValueError.",
    setup={},
    solution={
        "duration.py": "import re\n\nPAT = re.compile(r'(?:(\\d+)d)?(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?')\n\n\n"
        "def parse_duration(s):\n    s = s.strip()\n    m = PAT.fullmatch(s)\n    if not s or not m:\n"
        "        raise ValueError(s)\n    d, h, mi, se = (int(g) if g else 0 for g in m.groups())\n"
        "    return d * 86400 + h * 3600 + mi * 60 + se\n"
    },
    check=lambda w: compare_cases(
        w,
        "from duration import parse_duration\n",
        [
            ("parse_duration('1h30m')", 5400),
            ("parse_duration('45s')", 45),
            ("parse_duration(' 2h5s ')", 7205),
            ("parse_duration('1d2h')", 93600),
            ("parse_duration('0s')", 0),
            ("parse_duration('90m')", 5400),
            ("parse_duration('')", ValueError),
            ("parse_duration('5')", ValueError),
            ("parse_duration('1m1h')", ValueError),
            ("parse_duration('1h1h')", ValueError),
            ("parse_duration('1.5h')", ValueError),
        ],
    ),
)

task(
    id="impl_balanced",
    prompt="Create brackets.py with balanced(s), returning True when every (, [ and { in s is closed by the "
    "matching bracket in the right order. Text inside double-quoted strings is ignored, and inside such a string "
    "a backslash escapes the next character (so \\\" does not end the string). An unterminated string makes the "
    "whole input unbalanced.",
    setup={},
    solution={
        "brackets.py": "def balanced(s):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack, q, esc = [], False, False\n"
        "    for c in s:\n        if q:\n            if esc:\n                esc = False\n            elif c == '\\\\':\n"
        "                esc = True\n            elif c == '\"':\n                q = False\n        elif c == '\"':\n"
        "            q = True\n        elif c in '([{':\n            stack.append(c)\n        elif c in pairs:\n"
        "            if not stack or stack.pop() != pairs[c]:\n                return False\n"
        "    return not stack and not q\n"
    },
    check=lambda w: compare_cases(
        w,
        "from brackets import balanced\n",
        [
            ("balanced('([]{})')", True),
            ("balanced('([)]')", False),
            ("balanced('f(\"(\")')", True),
            ("balanced('f(\"\\\\\"(\")')", True),
            ("balanced('\"unterminated')", False),
            ("balanced('')", True),
            ("balanced(')(')", False),
            ("balanced('{\"a\\\\\\\\\"}')", True),
            ("balanced('[\"]\"')", False),
        ],
    ),
)

task(
    id="impl_luhn",
    prompt="Create luhn.py with valid(number), checking a card number with the Luhn algorithm. The input is a "
    "string; single spaces between digits are allowed and ignored. Return False if, after removing spaces, there "
    "are fewer than two characters or any character is not a digit 0 to 9.",
    setup={},
    solution={
        "luhn.py": "def valid(number):\n    s = number.replace(' ', '')\n"
        "    if len(s) < 2 or not all(c in '0123456789' for c in s):\n        return False\n    total = 0\n"
        "    for i, c in enumerate(reversed(s)):\n        d = int(c)\n        if i % 2:\n            d *= 2\n"
        "            if d > 9:\n                d -= 9\n        total += d\n    return total % 10 == 0\n"
    },
    check=lambda w: compare_cases(
        w,
        "from luhn import valid\n",
        [
            ("valid('4539 3195 0343 6467')", True),
            ("valid('8273 1232 7352 0569')", False),
            ("valid('059')", True),
            ("valid('0')", False),
            ("valid(' 0')", False),
            ("valid('055 444 285')", True),
            ("valid('055a 444 285')", False),
            ("valid('091')", True),
            ("valid('٣٤')", False),
        ],
    ),
)
