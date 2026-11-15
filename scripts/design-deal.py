#!/usr/bin/env python3
"""Deal distinct design directions from a style catalog, avoiding recently used choices.

  design-deal.py deal [--n 3] [--mood playful,warm] [--seed N] [--json]
  design-deal.py record <slug> --palette ID --type ID --layout ID --motion ID --surface ID
  design-deal.py list [axis]

History: .ba/design/history.json in the current directory (last HISTORY_WINDOW entries are avoided).
"""
import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

AXES = ("palette", "type", "layout", "motion", "surface")
HISTORY_WINDOW = 6
CATALOG = Path(__file__).resolve().parent.parent / "skills" / "design" / "references" / "catalog.json"
HISTORY = Path(".ba") / "design" / "history.json"


def load_catalog(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_history():
    if not HISTORY.is_file():
        return []
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def recent_ids(history, axis):
    return {h.get(axis) for h in history[-HISTORY_WINDOW:]}


def rank(items, mood, used, rng):
    def bucket(it):
        fresh = it["id"] not in used
        match = bool(mood & set(it["tags"]))
        return (not fresh, not match)

    shuffled = items[:]
    rng.shuffle(shuffled)
    return sorted(shuffled, key=bucket)  # stable: shuffle order kept inside each bucket


def deal(catalog, n, mood, history, rng):
    dirs = [{} for _ in range(n)]
    for axis in AXES:
        ranked = rank(catalog[axis], mood, recent_ids(history, axis), rng)
        if len(ranked) < n:
            sys.exit(f"catalog axis '{axis}' has fewer than {n} items")
        picks = ranked[:n]
        # last direction of 3+ is a wildcard: freshest item that ignores the mood, so options diverge
        if n >= 3 and mood:
            off = [it for it in ranked if not (mood & set(it["tags"])) and it not in picks[:-1]]
            used = recent_ids(history, axis)
            off = [it for it in off if it["id"] not in used] or off
            if off:
                picks[-1] = off[0]
        for d, it in zip(dirs, picks):
            d[axis] = it
    for i, d in enumerate(dirs):
        d["wildcard"] = bool(n >= 3 and mood and i == n - 1)
    return dirs


def fmt(d, i):
    p = d["palette"]
    lines = [f"[{chr(65 + i)}]{' (wildcard)' if d['wildcard'] else ''}",
             f"  palette  {p['id']}: " + " ".join(f"{k}={v}" for k, v in p["hex"].items()),
             f"  type     {d['type']['id']}: {d['type']['display']} / {d['type']['body']}",
             f"  layout   {d['layout']['id']}: {d['layout']['idea']}",
             f"  motion   {d['motion']['id']}: {d['motion']['idea']}",
             f"  surface  {d['surface']['id']}: {d['surface']['idea']}"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=str(CATALOG))
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deal")
    d.add_argument("--n", type=int, default=3)
    d.add_argument("--mood", default="")
    d.add_argument("--seed", type=int)
    d.add_argument("--json", action="store_true")
    r = sub.add_parser("record")
    r.add_argument("slug")
    for axis in AXES:
        r.add_argument(f"--{axis}")
    ls = sub.add_parser("list")
    ls.add_argument("axis", nargs="?", choices=AXES)
    a = ap.parse_args(argv)
    catalog = load_catalog(a.catalog)

    if a.cmd == "deal":
        rng = random.Random(a.seed)
        mood = {t.strip() for t in a.mood.split(",") if t.strip()}
        dirs = deal(catalog, a.n, mood, load_history(), rng)
        print(json.dumps(dirs, indent=1) if a.json else "\n".join(fmt(x, i) for i, x in enumerate(dirs)))
        return 0

    if a.cmd == "record":
        entry = {"slug": a.slug, "date": date.today().isoformat()}
        for axis in AXES:
            v = getattr(a, axis)
            if v is None:
                continue
            if v not in {it["id"] for it in catalog[axis]}:
                print(f"unknown {axis} id: {v}", file=sys.stderr)
                return 2
            entry[axis] = v
        hist = load_history()
        hist.append(entry)
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(hist, indent=1), encoding="utf-8")
        print(f"recorded {a.slug} -> {HISTORY}")
        return 0

    for axis in ([a.axis] if a.axis else AXES):
        print(f"{axis}: " + ", ".join(f"{it['id']}[{'/'.join(it['tags'])}]" for it in catalog[axis]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
