#!/usr/bin/env bash
# Prints BUILD=/TEST=/LINT= lines for the repo in $1 (default: cwd).
# .ba/commands.env overrides detection.
set -euo pipefail
cd "${1:-.}"
if [[ -f .ba/commands.env ]]; then
  cat .ba/commands.env
  if ! grep -q '^TEST_FAST=' .ba/commands.env; then
    T_VAL=$(grep '^TEST=' .ba/commands.env | cut -d= -f2- || true)
    [[ -n "$T_VAL" ]] && echo "TEST_FAST=$T_VAL"
  fi
  exit 0
fi

B=""; T=""; TF=""; L=""
has() { command -v "$1" >/dev/null 2>&1; }
pkg_script() { [[ -f package.json ]] && node -e "process.exit(require('./package.json').scripts?.['$1']?0:1)" 2>/dev/null; }

if [[ -f package.json ]]; then
  PM=npm
  [[ -f pnpm-lock.yaml ]] && PM=pnpm
  [[ -f yarn.lock ]] && PM=yarn
  [[ -f bun.lockb || -f bun.lock ]] && PM=bun
  pkg_script build && B="$PM run build"
  [[ -z $B && -f tsconfig.json ]] && B="npx tsc --noEmit"
  pkg_script test && T="$PM test"
  if pkg_script test:fast; then TF="$PM run test:fast"
  elif pkg_script test:unit; then TF="$PM run test:unit"
  elif grep -q '"vitest"' package.json; then TF="npx vitest run --exclude='**/*.e2e.*' --exclude='**/*.integration.*'"
  elif grep -q '"jest"' package.json; then TF="npx jest --testPathIgnorePatterns='e2e|integration'"
  else TF="$T"
  fi
  pkg_script lint && L="$PM run lint"
elif compgen -G "*.sln" >/dev/null || compgen -G "*.csproj" >/dev/null || compgen -G "*/*.csproj" >/dev/null; then
  B="dotnet build --nologo -v q"
  T="dotnet test --nologo -v q"
  TF="dotnet test --nologo -v q --filter 'Category!=Slow&Category!=Integration'"
elif [[ -f Cargo.toml ]]; then
  B="cargo build -q"
  T="cargo test -q"
  TF="cargo test -q --lib"
  L="cargo clippy -q -- -D warnings"
elif [[ -f go.mod ]]; then
  B="go build ./..."
  T="go test ./..."
  TF="go test -short ./..."
  L="go vet ./..."
elif [[ -f gradlew ]]; then
  B="./gradlew build -x test -q"
  T="./gradlew test -q"
  TF="./gradlew test -x integrationTest -q"
elif [[ -f pom.xml ]]; then
  B="mvn -q -DskipTests package"
  T="mvn -q test"
  TF="mvn -q test -Dtest='!*IT,*Test'"
elif [[ -f pyproject.toml || -f setup.py || -f requirements.txt ]]; then
  PY=python3; [[ -f uv.lock ]] && PY="uv run python"
  B="$PY -m compileall -q ."
  T="$PY -m pytest -q"
  TF="$PY -m pytest -q -m 'not slow and not integration'"
  has ruff && L="ruff check ."
elif [[ -f Makefile ]]; then
  B="make"
  grep -q '^test:' Makefile && T="make test"
  grep -q '^test-fast:' Makefile && TF="make test-fast" || TF="$T"
fi
echo "BUILD=$B"
echo "TEST=$T"
echo "TEST_FAST=${TF:-$T}"
echo "LINT=$L"
