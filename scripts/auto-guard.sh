#!/usr/bin/env bash
# Stop hook: while /ba:auto is running IN THIS SESSION, refuse to stop.
# .ba/auto.lock holds the session id of the run that created it; other sessions ignore it.
DIR="${CLAUDE_PROJECT_DIR:-.}"
LOCK="$DIR/.ba/auto.lock"
COUNT="$DIR/.ba/auto.count"
[[ -f "$LOCK" ]] || exit 0

payload=$(cat 2>/dev/null)
sid=$(printf '%s' "$payload" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
owner=$(tr -d '[:space:]' < "$LOCK" 2>/dev/null)
# Stale lock from another session (interrupted run): never block that session.
[[ -n "$owner" && -n "$sid" && "$owner" != "$sid" ]] && exit 0

n=$(( $(cat "$COUNT" 2>/dev/null || echo 0) + 1 ))
MAX="${BA_AUTO_MAX_CONTINUES:-40}"
echo "$n" > "$COUNT"
(( n > MAX )) && exit 0   # safety valve

cat <<JSON
{"decision":"block","reason":"ba:auto still running (continue $n/$MAX). Re-read \${CLAUDE_PLUGIN_ROOT}/skills/auto/SKILL.md (your instructions may have been compacted) and .ba/auto.json (source of truth). Resume in_progress issues first, then the next issue not done/blocked/skipped. Do not ask the user anything. When every issue is processed: print the final report, then delete .ba/auto.lock and .ba/auto.count."}
JSON
