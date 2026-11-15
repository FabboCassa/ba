#!/usr/bin/env python3
"""Flag the usual tells of AI-generated UI in HTML/CSS/JSX/TSX/Vue/Svelte/Razor files.

  design-lint.py [--json] [--strict] [--allow rule,rule] <file|dir>...

Exit 1 on any error (or any finding with --strict). Per-file waiver: a comment containing
`design-lint: allow rule1,rule2` (use only for choices the approved DESIGN.md justifies).
"""
import argparse
import json
import re
import sys
from pathlib import Path

EXTS = {".html", ".htm", ".css", ".scss", ".sass", ".less", ".js", ".jsx", ".ts", ".tsx",
        ".vue", ".svelte", ".astro", ".cshtml", ".razor", ".erb", ".hbs", ".njk", ".liquid", ".php"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt", "out", "vendor", "bin",
             "obj", "coverage", ".ba", "__pycache__", ".venv", "venv"}
I = re.IGNORECASE

PURPLE = r"#(6366f1|8b5cf6|a855f7|7c3aed|9333ea|4f46e5|ec4899|d946ef|667eea|764ba2|c084fc|818cf8)\b"
LINE_RULES = [
    ("cream-terracotta", "error", re.compile(r"#(f4f1ea|f5f0e8|faf7f2|f3efe6|d97757|cc785c|c96442)\b", I),
     "cream/terracotta pair is the house look of AI pages"),
    ("ai-gradient", "error",
     re.compile(rf"gradient[^;\n]*{PURPLE}|\b(from|via|to)-(purple|violet|indigo|fuchsia)-\d00\b", I),
     "purple/indigo/pink gradient: the most recognised AI tell"),
    ("default-font", "warn",
     re.compile(r"(font-family|fontFamily|next/font|fonts\.googleapis)[^\n]*\b(Inter|Roboto|Poppins|Montserrat|Open Sans|Arial)\b", I),
     "default typeface: pick one chosen for this brief"),
    ("fade-up", "warn", re.compile(r"fade-?in-?up|fade-up|data-aos=", I),
     "fade-and-rise entrance: generic motion, use one authored moment instead"),
    ("eyebrow-caps", "warn",
     re.compile(r"(text-transform:\s*uppercase|\buppercase\b)[^\n]*(letter-spacing|tracking-)", I),
     "tracked ALL-CAPS eyebrow label"),
    ("hype-copy", "warn",
     re.compile(r"unlock the power|\bseamless(ly)?\b|elevate your|revolutioni[sz]e|supercharge|\bempower|"
                r"cutting-edge|game-changer|next-level|\bunleash|\beffortless(ly)?\b|harness the", I),
     "marketing filler copy: say plainly what it does"),
    ("arrow-cta", "warn", re.compile(r"→|&rarr;"), "arrow appended to link/button text"),
    ("emoji-icon", "warn", re.compile("[\U0001F680✨⚡\U0001F525\U0001F4A1\U0001F3AF]"),
     "emoji used as icon"),
]
COUNT_RULES = [  # flagged only past the threshold
    ("glass", 2, re.compile(r"backdrop-filter:\s*blur|backdrop-blur", I), "glassmorphism used repeatedly"),
    ("grey-shadow", 3, re.compile(r"rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0?\.1\s*\)", I),
     "same soft grey shadow everywhere"),
    ("middot-meta", 3, re.compile(r" · "), "'A · B · C' meta strings"),
]
ANIM = re.compile(r"@keyframes|animation\s*:|data-aos=|from ['\"](framer-motion|motion/react|gsap)['\"]|\bgsap\.", I)
REDUCED = re.compile(r"prefers-reduced-motion|useReducedMotion|reducedMotion", I)
ALLOW = re.compile(r"design-lint:\s*allow\s+([\w,\- ]+)", I)


def files(paths):
    for p in map(Path, paths):
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in EXTS and not SKIP_DIRS & set(f.relative_to(p).parts[:-1]):
                    yield f


def lint(paths, allow):
    out, counts, first_anim, reduced = [], {}, None, False
    for f in files(paths):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        waived = set(allow)
        for m in ALLOW.finditer(text):
            waived |= {x.strip() for x in m.group(1).replace(" ", ",").split(",") if x.strip()}
        reduced |= bool(REDUCED.search(text))
        for n, line in enumerate(text.splitlines(), 1):
            if first_anim is None and ANIM.search(line) and "no-reduced-motion" not in waived:
                first_anim = (str(f), n)
            for rule, sev, rx, msg in LINE_RULES:
                if rule not in waived and rx.search(line):
                    out.append({"file": str(f), "line": n, "severity": sev, "rule": rule, "message": msg})
            for rule, limit, rx, msg in COUNT_RULES:
                if rule in waived:
                    continue
                for _ in rx.finditer(line):
                    counts[rule] = counts.get(rule, 0) + 1
                    if counts[rule] == limit + 1:
                        out.append({"file": str(f), "line": n, "severity": "warn", "rule": rule, "message": msg})
    if first_anim and not reduced:
        out.append({"file": first_anim[0], "line": first_anim[1], "severity": "error",
                    "rule": "no-reduced-motion", "message": "animation without a prefers-reduced-motion path"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--allow", default="")
    a = ap.parse_args(argv)
    found = lint(a.paths, {x for x in a.allow.split(",") if x})
    if a.json:
        print(json.dumps(found, indent=1))
    else:
        for x in found:
            print(f"{x['file']}:{x['line']}  {x['severity'].upper():5}  {x['rule']}  {x['message']}")
        errs = sum(x["severity"] == "error" for x in found)
        print(f"design-lint: {errs} errors, {len(found) - errs} warnings")
    fail = any(x["severity"] == "error" for x in found) or (a.strict and found)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
