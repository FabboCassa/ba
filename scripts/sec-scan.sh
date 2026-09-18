#!/usr/bin/env bash
# Deterministic security scanners, zero LLM tokens. Raw output in .ba/security/raw/, short summary on stdout.
# Secrets are ALWAYS redacted in what this script prints.
# Usage: sec-scan.sh secrets [--tree]     tree + full git history (--tree: working tree only)
#        sec-scan.sh code
#        sec-scan.sh deps [--id <GHSA-or-CVE>]   with --id: exit 1 if that advisory is still reported
# Exit: 0 clean, 1 findings, 2 usage/tool error. Missing tools are reported as "NOT CHECKED".
set -uo pipefail
MODE="${1:-}"; shift || true
TREE=0; ID=""
while [[ $# -gt 0 ]]; do case "$1" in --tree) TREE=1;; --id) ID="$2"; shift;; *) echo "unknown arg $1"; exit 2;; esac; shift; done
R=.ba/security/raw; mkdir -p "$R"
has() { command -v "$1" >/dev/null 2>&1; }
FOUND=0
nc() { echo "NOT CHECKED: $*"; }

secrets() {
  if has gitleaks; then
    gitleaks dir . --redact --no-banner -f json -r "$R/gitleaks-tree.json" >/dev/null 2>&1; T=$?
    [[ $T == 1 ]] && FOUND=1
    if [[ $TREE == 0 ]]; then
      gitleaks git . --redact --no-banner -f json -r "$R/gitleaks-history.json" >/dev/null 2>&1; H=$?
      [[ $H == 1 ]] && FOUND=1
    fi
    if has jq; then
      for f in "$R"/gitleaks-tree.json "$R"/gitleaks-history.json; do
        [[ -s $f ]] || continue
        echo "== $(basename "$f" .json): $(jq length "$f")"
        jq -r '.[] | "  \(.File):\(.StartLine)  \(.RuleID)  commit=\(.Commit[0:8] // "-")"' "$f" | sort -u | head -50
      done
    else echo "gitleaks findings in $R (install jq for summary)"; fi
  else
    nc "gitleaks missing - using built-in regex (working tree only, less precise)"
    PAT='AKIA[0-9A-Z]{16}|-----BEGIN ([A-Z]+ )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|sk_live_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{35}|(password|passwd|pwd|secret|api[_-]?key|token)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{8,}|(Password|Pwd)=[^;"'"'"']{6,}'
    git ls-files -co --exclude-standard -z | xargs -0 grep -EInHo "$PAT" 2>/dev/null \
      | grep -Ev '(\.example|\.sample|\.md:|test.*fixture)' \
      | awk -F: '{v=$0; sub(/^[^:]*:[^:]*:/,"",v); printf "  %s:%s  ****%s\n",$1,$2,substr(v,length(v)-3)}' | head -50 > "$R/regex-tree.txt"
    [[ -s $R/regex-tree.txt ]] && { FOUND=1; echo "== regex-tree: $(wc -l < "$R/regex-tree.txt")"; cat "$R/regex-tree.txt"; }
  fi
  # tracked files that should not be in git
  git ls-files | grep -Ei '(^|/)(\.env(\.[^/]*)?|id_rsa[^/]*|[^/]*\.(pem|key|p12|pfx|jks|keystore|p8|mobileprovision|tfstate)|secrets\.json|local\.settings\.json|credentials[^/]*\.json|service-account[^/]*\.json)$' \
    | grep -Ev '\.(example|sample|template)$|\.env\.example' > "$R/tracked-sensitive.txt"
  [[ -s $R/tracked-sensitive.txt ]] && { FOUND=1; echo "== tracked sensitive files:"; sed 's/^/  /' "$R/tracked-sensitive.txt"; }
}

code() {
  if has semgrep; then
    semgrep scan --config p/default --metrics=off --json -q -o "$R/semgrep.json" . >/dev/null 2>&1
    has jq && { N=$(jq '.results|length' "$R/semgrep.json" 2>/dev/null || echo 0); echo "== semgrep: $N"
      jq -r '.results[] | "  \(.path):\(.start.line)  \(.extra.severity)  \(.check_id|split(".")|last)"' "$R/semgrep.json" | head -60; [[ $N -gt 0 ]] && FOUND=1; }
  else nc "semgrep missing (pipx install semgrep)"; fi
  if git ls-files '*.py' | grep -q .; then
    if has bandit; then bandit -r . -q -f json -o "$R/bandit.json" -x ./.venv,./venv,./node_modules >/dev/null 2>&1 || FOUND=1; echo "== bandit: $R/bandit.json"
    else nc "bandit missing (python)"; fi
  fi
  if [[ -f go.mod ]]; then has gosec && { gosec -quiet -fmt json -out "$R/gosec.json" ./... >/dev/null 2>&1 || FOUND=1; echo "== gosec: $R/gosec.json"; } || nc "gosec missing"; fi
  if git ls-files '*.csproj' | grep -q . && has dotnet; then
    dotnet build -v q -p:AnalysisMode=All -p:AnalysisModeSecurity=All 2>&1 | grep -E 'warning (CA2|CA3|CA5|SCS)[0-9]+' | sort -u > "$R/dotnet-security.txt"
    [[ -s $R/dotnet-security.txt ]] && { FOUND=1; echo "== dotnet security analyzers: $(wc -l < "$R/dotnet-security.txt")"; head -40 "$R/dotnet-security.txt" | sed 's/^/  /'; }
  fi
  if has gh; then gh api "repos/{owner}/{repo}/code-scanning/alerts?state=open&per_page=100" > "$R/gh-code-scanning.json" 2>/dev/null \
    && has jq && echo "== github code scanning: $(jq length "$R/gh-code-scanning.json")"; fi
}

deps() {
  rm -f "$R"/osv.json "$R"/*audit*.json "$R"/dotnet-vuln.txt "$R"/govulncheck.json "$R"/gh-dependabot.json
  if has osv-scanner; then
    osv-scanner scan source -r --format json . > "$R/osv.json" 2>/dev/null; [[ $? == 1 ]] && FOUND=1
    has jq && { echo "== osv-scanner:"; jq -r '.results[]?.packages[]? | .package as $p | .vulnerabilities[]? | "  \($p.ecosystem) \($p.name)@\($p.version)  \(.id)  \((.aliases // [])|join(","))"' "$R/osv.json" | sort -u | head -80; }
  else nc "osv-scanner missing (https://google.github.io/osv-scanner/)"; fi
  [[ -f package-lock.json ]] && has npm && { npm audit --json > "$R/npm-audit.json" 2>/dev/null || FOUND=1; echo "== npm audit: $R/npm-audit.json"; }
  [[ -f pnpm-lock.yaml ]] && has pnpm && { pnpm audit --json > "$R/pnpm-audit.json" 2>/dev/null || FOUND=1; echo "== pnpm audit: $R/pnpm-audit.json"; }
  if [[ -f requirements.txt || -f pyproject.toml || -f poetry.lock ]]; then has pip-audit && { pip-audit -f json -o "$R/pip-audit.json" >/dev/null 2>&1 || FOUND=1; echo "== pip-audit: $R/pip-audit.json"; } || nc "pip-audit missing"; fi
  if git ls-files '*.csproj' | grep -q . && has dotnet; then
    dotnet list package --vulnerable --include-transitive > "$R/dotnet-vuln.txt" 2>&1
    grep -qiE '(Critical|High|Moderate|Low) ' "$R/dotnet-vuln.txt" && { FOUND=1; echo "== dotnet vulnerable packages:"; grep -E '^\s+>' "$R/dotnet-vuln.txt" | sort -u | head -40; }
  fi
  [[ -f go.mod ]] && { has govulncheck && { govulncheck -json ./... > "$R/govulncheck.json" 2>/dev/null; grep -q '"osv"' "$R/govulncheck.json" && FOUND=1; echo "== govulncheck: $R/govulncheck.json"; } || nc "govulncheck missing"; }
  [[ -f Cargo.lock ]] && { has cargo-audit && { cargo audit --json > "$R/cargo-audit.json" 2>/dev/null || FOUND=1; echo "== cargo audit: $R/cargo-audit.json"; } || nc "cargo-audit missing"; }
  if has gh; then gh api "repos/{owner}/{repo}/dependabot/alerts?state=open&per_page=100" > "$R/gh-dependabot.json" 2>/dev/null \
    && has jq && { N=$(jq length "$R/gh-dependabot.json"); echo "== dependabot open alerts: $N"
      jq -r '.[] | "  \(.dependency.package.ecosystem) \(.dependency.package.name)  \(.security_advisory.ghsa_id)  \(.security_advisory.severity)"' "$R/gh-dependabot.json" | head -40; }; fi
  if [[ -n $ID ]]; then
    compgen -G "$R/osv.json" >/dev/null || compgen -G "$R/*audit*.json" >/dev/null || compgen -G "$R/dotnet-vuln.txt" >/dev/null || compgen -G "$R/govulncheck.json" >/dev/null \
      || { echo "NOT CHECKED: no dependency scanner ran, cannot prove $ID is fixed"; exit 2; }
    if grep -rqs -- "$ID" "$R"/osv.json "$R"/*audit*.json "$R"/dotnet-vuln.txt "$R"/govulncheck.json; then   # dependabot excluded: it only updates after merge
      echo "STILL REPORTED: $ID"; exit 1; else echo "RESOLVED: $ID not reported by any scanner"; exit 0; fi
  fi
}

case "$MODE" in
  secrets) secrets;; code) code;; deps) deps;;
  *) echo "usage: sec-scan.sh secrets [--tree] | code | deps [--id X]"; exit 2;;
esac
echo "raw: $R"
exit $FOUND
