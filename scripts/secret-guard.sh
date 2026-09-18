#!/usr/bin/env bash
# Blocks commits/pushes/publishes that would ship secrets.
# Modes:
#   (no args)            Claude Code PreToolUse hook for Bash: reads hook JSON on stdin, exit 2 = block.
#   --git-hook pre-commit|pre-push   called by installed git hooks (exit 1 = block).
#   --install-git-hooks  install .git/hooks/pre-commit and pre-push (keeps existing hooks, chains them).
# Uses gitleaks when installed (gitleaks stdin, honors .gitleaksignore), else a built-in regex.
# Allow a false positive: add a line to .gitleaksignore (gitleaks fingerprint) or a path regex to .ba/secret-allow.
set -uo pipefail
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

PAT='AKIA[0-9A-Z]{16}|-----BEGIN ([A-Z]+ )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|sk_live_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{35}|(password|passwd|pwd|secret|api[_-]?key|token)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{8,}|(Password|Pwd)=[^;"'"'"']{6,}'
SENSITIVE='(^|/)(\.env(\.[^/]*)?|id_rsa[^/]*|[^/]*\.(pem|key|p12|pfx|jks|keystore|p8|mobileprovision|tfstate)|secrets\.json|local\.settings\.json|credentials[^/]*\.json|service-account[^/]*\.json)$'
SAFE='\.(example|sample|template)$'

allow() { [[ -f .ba/secret-allow ]] && grep -Evf .ba/secret-allow || cat; }

# $1 = unified diff / text on stdin. Prints redacted findings, returns 1 if any.
scan_text() {
  local tmp; tmp=$(mktemp)
  cat > "$tmp"
  if command -v gitleaks >/dev/null 2>&1; then
    local out; out=$(gitleaks stdin --redact --no-banner -v < "$tmp" 2>&1); local rc=$?
    rm -f "$tmp"
    [[ $rc == 1 ]] && { echo "$out" | grep -E '^(RuleID|Finding|File|Line)' | head -30; return 1; }
    return 0
  fi
  local hits; hits=$(grep -E '^\+' "$tmp" | grep -Ev '^\+\+\+' | grep -EIo "$PAT" | awk '{printf "  ****%s (%s)\n", substr($0,length($0)-3), substr($0,1,4)}' | head -20)
  rm -f "$tmp"
  [[ -n $hits ]] && { echo "$hits"; return 1; }
  return 0
}

check_files() {  # file list on stdin
  local bad; bad=$(grep -Ei "$SENSITIVE" | grep -Ev "$SAFE" | allow)
  [[ -n $bad ]] && { echo "sensitive files:"; echo "$bad" | sed 's/^/  /'; return 1; }
  return 0
}

as_diff() { while IFS= read -r -d '' f; do git diff --no-index --no-color /dev/null "$f" 2>/dev/null; done; }  # NUL-separated paths on stdin
untracked_as_diff() { git ls-files -o --exclude-standard -z | as_diff; }

push_range() {
  local up; up=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)
  if [[ -n $up ]]; then echo "$up..HEAD"; else echo "HEAD --not --remotes"; fi
}

run_check() {  # $1 = commit|commit-all|push|publish
  local r=0 out=""
  case "$1" in
    commit)     out+=$(git diff --cached | scan_text) || r=1
                out+=$'\n'$(git diff --cached --name-only --diff-filter=A | check_files) || r=1 ;;
    commit-all) out+=$( { git diff --cached; git diff; untracked_as_diff; } | scan_text) || r=1
                out+=$'\n'$( { git diff --cached --name-only --diff-filter=A; git ls-files -o --exclude-standard; } | check_files) || r=1 ;;
    push)       out+=$(eval git log -p --no-color "$(push_range)" | scan_text) || r=1
                out+=$'\n'$(eval git log --name-only --format= --diff-filter=A "$(push_range)" | sort -u | check_files) || r=1 ;;
    publish)    out+=$( { untracked_as_diff; git ls-files -z | as_diff; } | scan_text) || r=1
                out+=$'\n'$( { git ls-files; git ls-files -o --exclude-standard; } | check_files) || r=1 ;;
  esac
  [[ $r == 1 ]] && printf '%s\n' "$out" | sed '/^$/d'
  return $r
}

BLOCK_MSG="BLOCKED by ba secret-guard: this would publish secrets. Move the value to env vars / a secret store, add the file to .gitignore, unstage it (git rm --cached <file>). If the secret was already pushed anywhere, it must be ROTATED - removing it is not enough. False positive? add it to .gitleaksignore or a path regex to .ba/secret-allow."

case "${1:-}" in
  --install-git-hooks)
    G=$(git rev-parse --git-path hooks) || exit 1; mkdir -p "$G"
    cp "$SELF" "$G/ba-secret-guard.sh"   # copy: the plugin path changes on updates
    for h in pre-commit pre-push; do
      [[ -f $G/$h ]] && ! grep -q 'ba-secret-guard' "$G/$h" && mv "$G/$h" "$G/$h.ba-prev"
      cat > "$G/$h" <<HOOK
#!/usr/bin/env bash
D="\$(git rev-parse --git-path hooks)"
bash "\$D/ba-secret-guard.sh" --git-hook $h || exit 1
[ -f "\$D/$h.ba-prev" ] && exec bash "\$D/$h.ba-prev" "\$@"
exit 0
HOOK
      chmod +x "$G/$h"
    done
    echo "installed: $G/pre-commit $G/pre-push (previous hooks chained as *.ba-prev)"; exit 0 ;;
  --git-hook)
    [[ ${2:-} == pre-push ]] && m=push || m=commit
    out=$(run_check $m) && exit 0
    echo "$out" >&2; echo "$BLOCK_MSG" >&2; exit 1 ;;
esac

# PreToolUse hook mode
INPUT=$(cat)
if command -v jq >/dev/null 2>&1; then CMD=$(jq -r '.tool_input.command // empty' <<<"$INPUT")
else CMD=$(python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' <<<"$INPUT" 2>/dev/null || true); fi
[[ -z $CMD ]] && exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

MODES=()
if grep -Eq '(^|[;&|[:space:]])git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+commit' <<<"$CMD"; then
  if grep -Eq 'git[^;&|]*[[:space:]]add[[:space:]]|commit[^;&|]*[[:space:]]-[a-zA-Z]*a' <<<"$CMD"; then MODES+=(commit-all); else MODES+=(commit); fi
fi
grep -Eq '(^|[;&|[:space:]])git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+push' <<<"$CMD" && MODES+=(push)
grep -Eq '(npm|pnpm|yarn)[[:space:]]+publish|dotnet[[:space:]]+nuget[[:space:]]+push|twine[[:space:]]+upload|cargo[[:space:]]+publish|docker[[:space:]]+push|gh[[:space:]]+(release[[:space:]]+(create|upload)|gist[[:space:]]+create)|fastlane|gradlew?[^;&|]*publish' <<<"$CMD" && MODES+=(publish)
[[ ${#MODES[@]} -eq 0 ]] && exit 0

for m in "${MODES[@]}"; do
  if ! out=$(run_check "$m"); then
    { echo "$out"; echo "$BLOCK_MSG"; } >&2
    exit 2
  fi
done
exit 0
