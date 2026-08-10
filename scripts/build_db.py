#!/usr/bin/env python3
"""Minimal stand-in for the real build_db.py — CI-wiring test only."""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("usage: build_db.py data/solvers.json results.jsonl", file=sys.stderr)
        return 2

    db_path = Path(sys.argv[1])
    results_path = Path(sys.argv[2])

    db = json.loads(db_path.read_text()) if db_path.exists() else {"solvers": []}
    by_id = {s["id"]: s for s in db["solvers"]}

    for line in results_path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        by_id[rec["id"]] = rec

    db["solvers"] = list(by_id.values())
    db_path.write_text(json.dumps(db, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(db['solvers'])} solver(s) to {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
