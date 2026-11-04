#!/bin/zsh -f
# The daily job: validate the battery, run the day, publish the page and feed, push. Safe to rerun the same day:
# finished runs are skipped and an unchanged page makes no commit.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/bin:/bin:$HOME/.local/bin"
cd "${0:A:h}/.."
branch=$(cat .state/branch 2>/dev/null || echo main)
models=$(cat .state/models 2>/dev/null || echo sonnet,haiku)
day=$(date -u +%F)

git fetch -q origin
git checkout -q "$branch"
git pull -q --ff-only origin "$branch"
python3 tests/validate_battery.py > /dev/null
python3 -m weather.run --date "$day" --n 5 --workers 8 --models "$models"
python3 -m weather.publish
git add "runs/$day" docs README.md
if ! git diff --cached --quiet; then
  git commit -q -m "Weather for $day" -m "$(python3 -c 'import json;f=json.load(open("docs/feed.json"));d=f["days"][-1];print("; ".join(f"{m} {s[\"passes\"]}/{s[\"runs\"]}" for m,s in d["models"].items()))')"
  git push -q origin "$branch"
fi
