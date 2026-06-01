#!/usr/bin/env python3
"""Restore Opera files from Cursor local history (~/.config/Cursor/User/History)."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = Path.home() / ".config/Cursor/User/History"


def iter_history_entries() -> list[tuple[Path, str, int]]:
    rows: list[tuple[Path, str, int]] = []
    if not HISTORY.is_dir():
        return rows
    for entries_file in HISTORY.glob("*/entries.json"):
        try:
            data = json.loads(entries_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        resource = data.get("resource", "")
        marker = f"{ROOT.name}/"
        if marker not in resource and "AI-Trader/" not in resource and "Opera/" not in resource:
            continue
        for split_marker in (marker, "AI-Trader/", "Opera/"):
            if split_marker in resource:
                rel = resource.split(split_marker, 1)[-1]
                break
        else:
            continue
        target = ROOT / rel
        for entry in data.get("entries") or []:
            entry_id = entry.get("id")
            ts = int(entry.get("timestamp") or 0)
            if not entry_id:
                continue
            snapshot = entries_file.parent / entry_id
            if snapshot.is_file():
                rows.append((target, str(snapshot), ts))
    rows.sort(key=lambda row: row[2])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore files from Cursor local history.")
    parser.add_argument("--list", action="store_true", help="List recoverable files")
    parser.add_argument("--apply", action="store_true", help="Restore latest snapshot per file")
    parser.add_argument("--out", type=Path, help="Copy snapshots here instead of overwriting")
    args = parser.parse_args()

    latest: dict[Path, tuple[str, int]] = {}
    for target, snapshot, ts in iter_history_entries():
        prev = latest.get(target)
        if prev is None or ts >= prev[1]:
            latest[target] = (snapshot, ts)

    if not latest:
        print("No Opera snapshots found in Cursor history.")
        return 1

    if args.list or not args.apply:
        print("Recoverable files (latest snapshot):")
        for target in sorted(latest, key=lambda p: str(p)):
            snapshot, ts = latest[target]
            exists = "exists" if target.is_file() else "missing"
            print(f"  {target.relative_to(ROOT)}  [{exists}]  <- {snapshot}")
        if not args.apply:
            print("\nRe-run with --apply to restore (or --out DIR for copies).")
        return 0

    for target, (snapshot, _ts) in sorted(latest.items()):
        dest = (args.out / target.relative_to(ROOT)) if args.out else target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot, dest)
        print(f"restored {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
