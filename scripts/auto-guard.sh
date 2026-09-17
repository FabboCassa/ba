#!/usr/bin/env bash
# Stop hook (Ralph-loop style): while /ba:auto is running, refuse to stop.
# /ba:auto creates .ba/auto.lock at start and removes it after the final report.
DIR="${CLAUDE_PROJECT_DIR:-.}"
LOCK="$DIR/.ba/auto.lock"
[[ -f "$LOCK" ]] || exit 0
n=$(( $(cat "$LOCK" 2>/dev/null || echo 0) + 1 ))
MAX="${BA_AUTO_MAX_CONTINUES:-40}"
if (( n > MAX )); then
  echo "$n" > "$LOCK"
  exit 0   # safety valve: let it stop
fi
echo "$n" > "$LOCK"
cat <<JSON
{"decision":"block","reason":"ba:auto still running (continue $n/$MAX). Read .ba/auto.json, resume the queue from the next issue not done/blocked/skipped. Do not ask the user anything. When every issue is processed: print the final report, then delete .ba/auto.lock."}
JSON
