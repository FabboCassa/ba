#!/usr/bin/env bash
# blender-vc — Git + Git LFS setup for Blender asset projects (idempotent).
# Usage: blender-vc.sh init [dir]    configure LFS tracking + ignores
#        blender-vc.sh status [dir]  key=value report
# Exit: 0 ok | 2 not a git repo | 3 git-lfs missing
set -euo pipefail

cmd="${1:-status}"
dir="${2:-.}"
cd "$dir"

MARK="# ba:blender (managed by ba blender-vc)"
LFS_PATTERNS=(
  "*.blend" "*.fbx" "*.glb" "*.gltf.bin" "*.abc" "*.usd" "*.usdc" "*.usdz" "*.vdb"
  "*.exr" "*.hdr" "*.psd" "*.kra" "*.spp"
  "art/**/*.png" "art/**/*.jpg" "art/**/*.jpeg" "art/**/*.webp" "art/**/*.tga" "art/**/*.tif"
  "art/**/*.mp4" "art/**/*.mov" "art/**/*.wav"
)
IGNORES=("*.blend[0-9]" "*.blend[0-9][0-9]" "*.blend@" "art/**/cache/" "art/**/.tmp/")

in_repo() { git rev-parse --is-inside-work-tree >/dev/null 2>&1; }
has_lfs() { git lfs version >/dev/null 2>&1; }

add_block() { # file, lines...
  local f="$1"; shift
  [ -f "$f" ] && grep -qxF "$MARK" "$f" && return 0
  { [ -s "$f" ] && [ -n "$(tail -c1 "$f")" ] && echo; echo "$MARK"; printf '%s\n' "$@"; } >>"$f"
}

case "$cmd" in
  init)
    in_repo || { echo "not a git repo: run 'git init' first" >&2; exit 2; }
    has_lfs || { echo "git-lfs missing: install from https://git-lfs.com then rerun" >&2; exit 3; }
    git lfs install --local >/dev/null
    attrs=()
    for p in "${LFS_PATTERNS[@]}"; do attrs+=("$p filter=lfs diff=lfs merge=lfs -text"); done
    attrs+=("*.scene.json text eol=lf")
    add_block .gitattributes "${attrs[@]}"
    add_block .gitignore "${IGNORES[@]}"
    plain=$(git ls-files -- '*.blend' | while read -r f; do
      [ "$(git check-attr filter -- "$f" | awk '{print $3}')" = lfs ] && git lfs ls-files -n | grep -qxF "$f" || echo "$f"
    done)
    [ -n "$plain" ] && echo "WARN: .blend already committed outside LFS (history rewrite needed: git lfs migrate import --include='*.blend'):" && echo "$plain"
    echo "blender-vc: ok"
    ;;
  status)
    echo "git=$(in_repo && echo yes || echo no)"
    echo "lfs=$(has_lfs && echo yes || echo missing)"
    echo "attributes=$( [ -f .gitattributes ] && grep -qxF "$MARK" .gitattributes && echo ok || echo missing)"
    if in_repo; then
      echo "lfs_files=$(has_lfs && git lfs ls-files -n 2>/dev/null | wc -l | tr -d ' ' || echo 0)"
      echo "remote=$(git remote get-url origin 2>/dev/null || echo none)"
      echo "branch=$(git branch --show-current)"
    fi
    ;;
  *)
    sed -n '2,6p' "$0"; exit 1
    ;;
esac
