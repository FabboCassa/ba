---
name: secure
description: Security audit - plaintext secrets (tree + git history + what gets published), known vulnerable code patterns, vulnerable dependencies, and compliance with the target platform's official publishing/security requirements (fetched online from official sources only). Proposes fixes and turns the approved ones into ba issues.
disable-model-invocation: true
argument-hint: "[secrets|code|deps|platform ...] [web=yes|no] [auto]"
allowed-tools: Read Grep Glob Write Edit Agent Skill AskUserQuestion WebSearch WebFetch Bash(git *) Bash(gh *) Bash(bash *) Bash(jq *) Bash(npm *) Bash(npx *) Bash(pnpm *) Bash(dotnet *) Bash(python* *) Bash(pip-audit *) Bash(go *) Bash(govulncheck *) Bash(cargo *) Bash(gitleaks *) Bash(osv-scanner *) Bash(semgrep *)
---

Args: $ARGUMENTS
Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`

Areas = args among `secrets code deps platform` (none → all). `AUTO` = args contain `auto`.

# Hard rules
- **Never print, log, quote, commit or put in an issue a secret value.** Refer to secrets as `file:line <type> ****<last 4>`.
- Security details never go public: the full report lives in `.ba/security/` (always gitignored). On a **public** repo (`gh repo view --json visibility`), issues get neutral titles/bodies ("Harden input validation in OrderController") and point to `.ba/security/<ID>.md`; critical/high on public repos are also offered as a private GitHub Security Advisory draft (`gh api -X POST repos/{o}/{r}/security-advisories`) instead of an issue if the user prefers.
- Nothing is fixed inside this skill except `.gitignore` additions and the guard installs in step 6. Fixes = issues → `implement`/`ship`/`auto`.
- No git history rewrite, no force push, ever, without an explicit "sì" from the user in this session (never in `AUTO`). Rotating a leaked key comes first anyway: rewriting history does not un-leak it.
- Only findings with evidence. Report honestly what could NOT be checked (tool missing, no network, no permission).

# 0. Setup (silent)
- `mkdir -p .ba/security`; add `.ba/security/` and `.ba/logs/` to `.gitignore`.
- `bash $S/detect.sh .`; `gh repo view --json nameWithOwner,visibility,defaultBranchRef`.
- **Platforms**: detect from files — web (package.json with a front-end/server framework, index.html, Dockerfile exposing HTTP), android (AndroidManifest.xml, `com.android.application`), ios (*.xcodeproj, Info.plist), cross-platform (MAUI, Flutter, React Native, Capacitor, Electron), windows store (Package.appxmanifest/MSIX), browser extension (manifest.json with `manifest_version`), package registry (npm `publishConfig`/no `private`, *.nuspec/`IsPackable`, pyproject `[project]`, Cargo `[package]` publish), container image.
  Stored in `.ba/config.json` → `"platforms":[...]`. If not stored and not `AUTO`: confirm with AskUserQuestion (detected set first `(Consigliato)`, multiSelect).
- **Online research permission** (`.ba/config.json` → `"web":"allow"|"deny"`): arg `web=yes|no` overrides and is saved. Missing and not `AUTO` → ask ONCE: "Posso cercare online, solo su siti ufficiali, requisiti di pubblicazione e vulnerabilità recenti? La risposta viene salvata." (Consigliato: sì). Missing in `AUTO` → `deny` for this run, noted in the report.

# 1. Secrets & what gets published
Run `bash $S/sec-scan.sh secrets` (gitleaks on working tree AND full history, redacted; built-in regex fallback if gitleaks missing). Then check yourself:
- **Tracked files that should never be tracked**: Read `${CLAUDE_SKILL_DIR}/references/tracked-file-patterns.md` for the full checklist of file patterns, ignore coverage, and publish dry-run commands.
- **GitHub side** (ignore 403/404 silently): `gh api repos/{o}/{r}/secret-scanning/alerts?state=open`; workflows (`.github/workflows/*`): secrets echoed, `pull_request_target` + checkout of PR head, `permissions` missing/too broad, third-party actions not pinned to a SHA.
Any live secret found → **before anything else** print a short "AZIONE URGENTE" block: which credential type, where, "ruota/revoca la chiave sul provider ora", then continue. Issue for it: label `needs-human` (rotation) + separate `ba` issue for code-side fix (move to env/secret store, add ignore rule, add guard). History cleanup only as an optional, user-approved step listed in the report.

# 2. Code vulnerabilities
`bash $S/sec-scan.sh code` (semgrep `p/default` + language rules, bandit, gosec, .NET analyzers via build warnings, eslint security plugin if configured; GitHub code-scanning alerts via `gh api` if enabled).
Then **ba:auditor** (mode `security`) on entry points (HTTP handlers, deep links/intents, IPC, file/URL inputs, deserializers, auth code), guided by OWASP Top 10 (web/API) and OWASP MASVS (mobile): injection (SQL/NoSQL/command/LDAP), broken access control/IDOR, authn/session flaws, SSRF, path traversal, unsafe deserialization, XSS/CSRF, weak crypto/random, hardcoded crypto keys, sensitive data in logs, missing rate limiting on auth, CORS `*` with credentials, insecure TLS config, mobile: cleartext traffic, exported components, WebView JS bridges, insecure local storage, `debuggable`/`allowBackup`, missing cert validation.
Scanner hits are triaged: false positive → listed with the reason, not issued.

# 3. Dependencies
`bash $S/sec-scan.sh deps` → osv-scanner on all lockfiles + native audits (`npm/pnpm/yarn audit`, `pip-audit`, `dotnet list package --vulnerable --include-transitive`, `govulncheck ./...`, `cargo audit`) + `gh api repos/{o}/{r}/dependabot/alerts?state=open`.
For each vulnerable package: advisory id (GHSA/CVE), severity, fixed version, direct/transitive, **reachable?** (is the vulnerable function/module used — grep). With `web=allow` also check: CISA KEV (actively exploited → priority critical), EOL of runtime/framework versions on the vendor's official lifecycle page.
Also flag: abandoned packages (no release > 2 years + known issues), typosquat-looking names, install scripts from unknown packages.

# 4. Platform compliance (`web=allow` only; otherwise list as "not checked")
Research with WebSearch/WebFetch **restricted to official domains**: Read `${CLAUDE_SKILL_DIR}/references/allowed-domains.md` for the full list.
Cache: `.ba/security/requirements-<platform>.md` with, for each requirement: text, **source URL, fetch date**. Reuse if < 30 days old, else refresh. Also `.ba/security/advisories-<date>.md` for the newest relevant threats (last 90 days) for the stack in use.
What to verify per platform: Read `${CLAUDE_SKILL_DIR}/references/platform-checklists.md` for the full per-platform checklist (android, ios, web, desktop/extension/registry/containers).
Each gap = finding with Kind `config` or `feature` and the source URL in the finding.

# 5. Report + approval
`.ba/security/report-<YYYY-MM-DD>.md` (gitignored, never committed):
```
# Security audit <date>   Status: draft
Repo: <name> (<public|private>)  Platforms: <list>  Online research: <allow|deny>  Sources refreshed: <date>
| ID | Sev | Area | Kind | Finding (evidence, secrets masked) | Fix proposal |
| S1 | critical | secrets | secret | appsettings.Production.json:12 SQL conn string with password ****a9f2, in history since 3f2c1e0 | move to user-secrets/env, ignore file, rotate password (needs-human) |
## Details (one ### per ID: evidence, fix, acceptance bullets, advisory/source URLs)
## Needs human (rotations, store console forms, legal texts)
## False positives / accepted risks
## Not checked (and why)
```
Severity: critical (live secret, exploitable RCE/auth bypass, KEV) > high > medium > low. Show the user only the table + "Quali trasformo in issue? (tutte / S1 S4 … / nessuna)". In `AUTO`: all critical/high/medium.

# 6. Guards (install once, idempotent)
- **Commit/push guard** (already active via plugin hook `secret-guard.sh`): tell the user it is on. Offer (skip in `AUTO`) to also install it as git `pre-commit` + `pre-push` hooks for commits made outside Claude: `bash $S/secret-guard.sh --install-git-hooks`.
- **Weekly CI scan**: if `.github/workflows/ba-security.yml` is missing, add it from `${CLAUDE_SKILL_DIR}/../../templates/security.yml` as its own issue (Kind `config`, label `ba security`), so it goes through PR review like everything else.

# 7. Issues + next
Follow `${CLAUDE_SKILL_DIR}/../issues/SKILL.md` using the report as source (confirmation already done), one issue per approved ID, labels `ba` + `security` (+ `needs-human` for manual-only items, which `auto` skips). Body has `Kind:` and acceptance bullets. Proof per Kind:
- `security` (code vuln): a test that **performs the attack** (malicious input, unauthorized request, traversal path) and asserts it is rejected → red before the fix, green after (normal prove-test).
- `dep-upgrade`: acceptance = `bash $S/sec-scan.sh deps --id <GHSA/CVE>` no longer reports it + gate green.
- `secret`: acceptance = `bash $S/sec-scan.sh secrets --tree` clean for that file + ignore rule present + app reads value from env/secret store (test).
- `config`: acceptance = a check command or test asserting the setting (e.g. manifest value, header present in response test).
Public repo → neutral issue text, details only in `.ba/security/<ID>.md`.
Output: urgent block (if any) + issue list + `Next: /ba:ship` or `/ba:auto`. With `AUTO`: invoke skill `ba:auto` directly.
