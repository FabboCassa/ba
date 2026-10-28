#!/usr/bin/env bash
# Stop hook: while /ba:auto is running IN THIS SESSION, refuse to stop.
# Supports both Claude Code (decision: "block") and Google Antigravity / agy (decision: "continue").
payload=$(cat 2>/dev/null || true)
is_agy=0
grep -q '"conversationId"' <<<"$payload" && is_agy=1

DIR="${CLAUDE_PROJECT_DIR:-}"
if [[ -z "$DIR" && $is_agy -eq 1 ]]; then
  if command -v jq >/dev/null 2>&1; then
    DIR=$(jq -r '.workspacePaths[0] // empty' <<<"$payload" 2>/dev/null)
  fi
fi
DIR="${DIR:-.}"

LOCK="$DIR/.ba/auto.lock"
COUNT="$DIR/.ba/auto.count"
WAITING="$DIR/.ba/auto.waiting"
[[ -f "$LOCK" ]] || exit 0
# Agents are running in the background: stopping is correct, the run resumes on their notification.
[[ -s "$WAITING" ]] && exit 0

if [[ $is_agy -eq 1 ]]; then
  sid=$(printf '%s' "$payload" | sed -n 's/.*"conversationId"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
else
  sid=$(printf '%s' "$payload" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
fi
owner=$(tr -d '[:space:]' < "$LOCK" 2>/dev/null)
# Stale lock from another session (interrupted run): never block that session.
[[ -n "$owner" && -n "$sid" && "$owner" != "$sid" ]] && exit 0

n=$(( $(cat "$COUNT" 2>/dev/null || echo 0) + 1 ))
MAX="${BA_AUTO_MAX_CONTINUES:-40}"
echo "$n" > "$COUNT"
(( n > MAX )) && exit 0   # safety valve

DECISION="block"
[[ $is_agy -eq 1 ]] && DECISION="continue"

cat <<JSON
{"decision":"$DECISION","reason":"ba:auto still running (continue $n/$MAX). Re-read skills/auto/SKILL.md (your instructions may have been compacted) and .ba/auto.json (source of truth). Resume in_progress issues first, then the next issue not done/blocked/skipped. Route implementer to pro (Gemini 4 Argon / opus), verifier to flash (Gemini 3.8 Flash / sonnet), reviewer to flash_lite (Gemini 3.8 Flash Low). Do not ask the user anything. When every issue is processed: print the final report, then delete .ba/auto.lock and .ba/auto.count."}
JSON
