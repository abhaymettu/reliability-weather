#!/bin/zsh -f
# Install (or reinstall) the daily launchd job for this checkout. Undo: launchctl bootout gui/$UID/local.abhay.reliability-weather
set -euo pipefail
repo="${0:A:h:h}"
dest="$HOME/Library/LaunchAgents/local.abhay.reliability-weather.plist"
sed "s#__REPO__#$repo#; s#__HOME__#$HOME#g" "$repo/scripts/local.abhay.reliability-weather.plist" > "$dest"
plutil -lint "$dest"
launchctl bootout "gui/$UID/local.abhay.reliability-weather" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$dest"
launchctl print "gui/$UID/local.abhay.reliability-weather" | grep -E "state|path" | head -3
