"""Read files, compute something exact, write an output file. Data is generated from fixed seeds at import time."""
import csv
import io
import json
import random
from collections import Counter, defaultdict
from decimal import ROUND_HALF_UP, Decimal

from weather.battery import files_equal

TASKS = []


def task(**kw):
    TASKS.append(kw)


def _csv(rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def _json_file(work, rel):
    try:
        return json.loads((work / rel).read_text()), ""
    except FileNotFoundError:
        return None, f"{rel} missing"
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"{rel} is not valid JSON: {e}"


def _cents(x):
    return float(Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# sales_by_region
_r = random.Random(101)
_regions = ["north", "south", "east", "west", "North ", "central"]
_sales = [["date", "region", "amount"]] + [
    [f"2026-10-{_r.randint(1, 31):02d}", _r.choice(_regions), f"{_r.randint(1, 99999) / 100:.2f}"] for _ in range(240)
]
_sales.insert(57, ["2026-10-07", "east", ""])
_sales.insert(130, ["2026-10-19", "south", "n/a"])
_totals = defaultdict(Decimal)
for _d, _reg, _amt in _sales[1:]:
    try:
        _totals[_reg.strip().lower()] += Decimal(_amt)
    except ArithmeticError:
        pass
_SALES_EXPECTED = {k: _cents(v) for k, v in sorted(_totals.items())}


def _check_sales(work):
    got, err = _json_file(work, "totals.json")
    if err:
        return False, err
    if got != _SALES_EXPECTED:
        return False, f"totals.json has {got!r}"
    return True, "totals match"


task(
    id="data_sales_totals",
    prompt="sales.csv has one row per sale. Write totals.json: a JSON object mapping each region to its total "
    "amount, rounded to 2 decimal places (as a JSON number). Region names should be compared after trimming "
    "whitespace and lowercasing, and the keys written in that normalized form. Rows whose amount is empty or not "
    "a number are skipped.",
    setup={"sales.csv": _csv(_sales)},
    solution={"totals.json": json.dumps(_SALES_EXPECTED)},
    check=_check_sales,
)

# log_errors
_r = random.Random(202)
_mods = ["auth", "db", "api", "cache", "billing", "search"]
_levels = ["INFO"] * 6 + ["WARN"] * 2 + ["ERROR"] * 2
_log_lines, _err = [], Counter()
for i in range(400):
    lvl, mod = _r.choice(_levels), _r.choice(_mods)
    _log_lines.append(f"2026-11-01T{i // 60 % 24:02d}:{i % 60:02d}:00Z [{lvl}] {mod}: event {i}")
    if lvl == "ERROR":
        _err[mod] += 1
_log_lines.insert(33, "2026-11-01T00:33:30Z [INFO] api: retry after ERROR in upstream")
_log_lines.insert(90, "    traceback continues [ERROR] db: not a real entry")
_ERR_CSV = "module,errors\n" + "".join(f"{m},{n}\n" for m, n in sorted(_err.items(), key=lambda kv: (-kv[1], kv[0])))

task(
    id="data_log_errors",
    prompt="app.log holds log lines of the form '<timestamp> [<LEVEL>] <module>: <message>'. Count the lines whose "
    "level is ERROR, per module. Lines that do not start with a timestamp are continuation lines and are not "
    "entries. Write errors.csv with the header 'module,errors' and one row per module that has at least one error, "
    "sorted by count descending and then module name ascending.",
    setup={"app.log": "\n".join(_log_lines) + "\n"},
    solution={"errors.csv": _ERR_CSV},
    check=lambda w: files_equal(w, "errors.csv", _ERR_CSV),
)

# join users and orders
_r = random.Random(303)
_users = [[str(i), f"user{i}", _r.choice(["us", "de", "in", "br"])] for i in range(1, 31)]
_orders = []
for oid in range(1, 121):
    uid = _r.choice([u[0] for u in _users[:24]] + ["99"])
    _orders.append({"order_id": oid, "user_id": int(uid), "total": _r.randint(100, 20000) / 100,
                    "status": _r.choice(["paid", "paid", "paid", "refunded"])})
_spent = defaultdict(Decimal)
for o in _orders:
    if o["status"] == "paid":
        _spent[o["user_id"]] += Decimal(str(o["total"]))
_JOIN_EXPECTED = [{"user": u[1], "country": u[2], "paid_total": _cents(_spent.get(int(u[0]), Decimal(0)))}
                  for u in _users]
_JOIN_EXPECTED.sort(key=lambda r: (-r["paid_total"], r["user"]))


def _check_join(work):
    got, err = _json_file(work, "report.json")
    if err:
        return False, err
    if got != _JOIN_EXPECTED:
        return False, "report.json differs from expected"
    return True, "report matches"


task(
    id="data_join_orders",
    prompt="users.csv lists users (id,name,country) and orders.jsonl has one order per line. Write report.json: a "
    "JSON list with one object per user in users.csv, {\"user\": name, \"country\": country, \"paid_total\": "
    "number}, where paid_total sums the totals of that user's orders with status 'paid', rounded to 2 decimals "
    "(0 for users with none). Orders for user ids not in users.csv are ignored. Sort by paid_total descending, "
    "then name ascending.",
    setup={"users.csv": _csv([["id", "name", "country"]] + _users),
           "orders.jsonl": "".join(json.dumps(o) + "\n" for o in _orders)},
    solution={"report.json": json.dumps(_JOIN_EXPECTED)},
    check=_check_join,
)

# dedupe contacts
_r = random.Random(404)
_people = [f"person{i}" for i in range(40)]
_contacts = [["name", "email", "created"]]
for i in range(90):
    p = _r.choice(_people)
    email = _r.choice([f"{p}@example.com", f" {p.upper()}@Example.com", f"{p}@example.com "])
    _contacts.append([p.title(), email, f"2025-{_r.randint(1, 12):02d}-{_r.randint(1, 28):02d}"])
_best = {}
for row in _contacts[1:]:
    key = row[1].strip().lower()
    if key not in _best or row[2] < _best[key][2]:
        _best[key] = row
_DEDUPE_CSV = "name,email,created\n" + "".join(
    f"{r[0]},{k},{r[2]}\n" for k, r in sorted(_best.items(), key=lambda kv: (kv[1][2], kv[0]))
)

task(
    id="data_dedupe_contacts",
    prompt="contacts.csv has name,email,created (an ISO date). Two rows are the same contact when their emails "
    "match after trimming whitespace and lowercasing. Keep, for each contact, the row with the earliest created "
    "date (if two tie, the one that appears first). Write clean.csv with the header 'name,email,created', the "
    "email written in its normalized form, sorted by created ascending, then email ascending.",
    setup={"contacts.csv": _csv(_contacts)},
    solution={"clean.csv": _DEDUPE_CSV},
    check=lambda w: files_equal(w, "clean.csv", _DEDUPE_CSV),
)

# deep merge config
_BASE = {"name": "svc", "port": 8080, "db": {"host": "localhost", "pool": {"min": 1, "max": 10}, "tags": ["a", "b"]},
         "features": {"x": True, "y": False}, "debug": False}
_OVER = {"port": 9090, "db": {"pool": {"max": 50}, "tags": ["c"], "host": None}, "features": {"z": True},
         "debug": None, "extra": {"k": [1, 2]}}


def _merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if v is None:
            out.pop(k, None)
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


_MERGED = _merge(_BASE, _OVER)


def _check_merge(work):
    got, err = _json_file(work, "merged.json")
    if err:
        return False, err
    return (got == _MERGED), ("merged.json matches" if got == _MERGED else f"merged.json has {got!r}")


task(
    id="data_config_merge",
    prompt="Write merged.json, the result of applying override.json on top of base.json with these rules: objects "
    "merge recursively key by key; any other value in the override (including a list) replaces the base value; "
    "a null in the override deletes that key from the result. Keys only in base are kept.",
    setup={"base.json": json.dumps(_BASE, indent=2), "override.json": json.dumps(_OVER, indent=2)},
    solution={"merged.json": json.dumps(_MERGED)},
    check=_check_merge,
)

# find TODOs across a tree
_r = random.Random(505)
_tree, _todos = {}, []
for d in ["app", "app/core", "lib", "tests"]:
    for f in range(3):
        rel = f"{d}/mod{f}.py"
        lines = []
        for ln in range(1, _r.randint(8, 20)):
            roll = _r.random()
            if roll < 0.12:
                lines.append(f"    x = {ln}  # TODO: item {d} {f} {ln}")
                _todos.append((rel, len(lines)))
            elif roll < 0.18:
                lines.append(f"    msg = 'TODO in a string is not a comment {ln}'")
            elif roll < 0.22:
                lines.append(f"    # todo lowercase is not counted {ln}")
            else:
                lines.append(f"    y = {ln}")
        _tree[rel] = "def f():\n" + "\n".join(lines) + "\n"
_todos = [(rel, n + 1) for rel, n in _todos]
_tree["notes.txt"] = "TODO: this file is not Python\n"
_TODO_TXT = "".join(f"{rel}:{n}\n" for rel, n in sorted(_todos))

task(
    id="data_find_todos",
    prompt="Find every comment containing 'TODO' (uppercase, after a # on the line, not inside a string) in the "
    "Python files (*.py) anywhere in this project. Write todos.txt with one line per occurrence, formatted "
    "'path:line' where path is relative to the project with forward slashes and line is 1-based, sorted by path "
    "and then line number.",
    setup=_tree,
    solution={"todos.txt": _TODO_TXT},
    check=lambda w: files_equal(w, "todos.txt", _TODO_TXT),
)

# inventory transactions
_r = random.Random(606)
_inv = {s: _r.randint(0, 20) for s in ["apple", "bolt", "cable", "drill", "epoxy"]}
_tx, _state, _rejected = [], dict(_inv), []
for i in range(1, 61):
    sku = _r.choice(list(_inv) + ["gizmo"])
    op = _r.choice(["add", "remove", "remove"])
    qty = _r.randint(1, 9)
    _tx.append(f"{op} {sku} {qty}")
    if op == "add":
        _state[sku] = _state.get(sku, 0) + qty
    elif _state.get(sku, 0) >= qty:
        _state[sku] -= qty
    else:
        _rejected.append(i)
_REJ_TXT = "".join(f"{n}\n" for n in _rejected)


def _check_inventory(work):
    got, err = _json_file(work, "inventory_after.json")
    if err:
        return False, err
    if got != _state:
        return False, f"inventory_after.json has {got!r}"
    return files_equal(work, "rejected.txt", _REJ_TXT)


task(
    id="data_inventory",
    prompt="inventory.json maps SKUs to stock counts. transactions.txt has one transaction per line, 'add SKU QTY' "
    "or 'remove SKU QTY', applied in order. An add of an unknown SKU creates it. A remove that would take a SKU "
    "below zero (or of an unknown SKU) is rejected and changes nothing. Write inventory_after.json with the final "
    "counts (every SKU, including ones at zero) and rejected.txt listing the 1-based line numbers of rejected "
    "transactions, one per line.",
    setup={"inventory.json": json.dumps(_inv, indent=2), "transactions.txt": "\n".join(_tx) + "\n"},
    solution={"inventory_after.json": json.dumps(_state), "rejected.txt": _REJ_TXT},
    check=_check_inventory,
)

# markdown table
_r = random.Random(707)
_table = [["item", "qty", "price", "note"]] + [
    [f"item-{i}", str(_r.randint(1, 500)), f"{_r.randint(1, 9999) / 100:.2f}", _r.choice(["", "fragile", "x|y"])]
    for i in range(1, 9)
]


def _md(rows):
    head, body = rows[0], rows[1:]
    numeric = [all(_isnum(r[c]) for r in body) for c in range(len(head))]
    esc = [[c.replace("|", "\\|") for c in r] for r in rows]
    widths = [max(len(r[c]) for r in esc) for c in range(len(head))]
    widths = [max(w, 3) for w in widths]

    def line(r):
        return "| " + " | ".join(
            (v.rjust(widths[c]) if numeric[c] else v.ljust(widths[c])) for c, v in enumerate(r)) + " |"

    sep = "| " + " | ".join(("-" * (widths[c] - 1) + ":") if numeric[c] else "-" * widths[c]
                            for c in range(len(head))) + " |"
    return "\n".join([line(esc[0]), sep, *map(line, esc[1:])]) + "\n"


def _isnum(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


_MD = _md(_table)

task(
    id="data_markdown_table",
    prompt="Convert table.csv to table.md, a Markdown table, exactly as follows. A column is numeric when every "
    "value below the header parses as a number. Escape each '|' inside a cell as '\\|'. Each column's width is the "
    "longest escaped cell in it (header included), at least 3. Every line is '| ' + cells joined by ' | ' + ' |'; "
    "numeric columns are right-aligned and the rest left-aligned, padded with spaces to the width. The second line "
    "is the separator: for a numeric column width-1 hyphens then ':', otherwise width hyphens. End the file with a "
    "newline.",
    setup={"table.csv": _csv(_table)},
    solution={"table.md": _MD},
    check=lambda w: files_equal(w, "table.md", _MD),
)
