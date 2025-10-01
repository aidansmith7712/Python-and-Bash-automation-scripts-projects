#!/usr/bin/env python3
"""
Timestamped file backup with optional recursion, retention pruning, and dry-run.
"""
import argparse, sys, shutil
from datetime import datetime, timedelta
from pathlib import Path

def backup(src: Path, dest: Path, pattern: str, recursive: bool, dry_run: bool):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_dir = dest / f"backup_{ts}"
    if not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)

    files = (src.rglob(pattern) if recursive else src.glob(pattern))
    copied = 0
    for f in files:
        if f.is_file():
            target = backup_dir / f.name
            print(f"[COPY] {f} -> {target}")
            if not dry_run:
                shutil.copy2(f, target)  # preserves metadata
            copied += 1
    print(f"Completed. {copied} file(s) {'would be ' if dry_run else ''}backed up to {backup_dir}")

def prune(dest: Path, retention_days: int, dry_run: bool):
    cutoff = datetime.now() - timedelta(days=retention_days)
    for p in dest.glob("backup_*"):
        try:
            stamp = datetime.strptime(p.name.replace("backup_",""), "%Y-%m-%d_%H-%M")
        except ValueError:
            continue
        if stamp < cutoff:
            print(f"[PRUNE] {p}")
            if not dry_run:
                shutil.rmtree(p, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser(description="Timestamped file backup")
    ap.add_argument("--src", required=True, type=Path, help="Source directory")
    ap.add_argument("--dest", required=True, type=Path, help="Destination directory")
    ap.add_argument("--pattern", default="*.txt", help="Glob pattern (e.g., *.pdf)")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--retention-days", type=int, default=0, help="Delete backups older than N days")
    ap.add_argument("--dry-run", action="store_true", help="Plan actions without writing")
    args = ap.parse_args()

    if not args.src.exists() or not args.src.is_dir():
        print(f"ERROR: Source directory not found: {args.src}", file=sys.stderr)
        sys.exit(2)
    args.dest.mkdir(parents=True, exist_ok=True)

    backup(args.src, args.dest, args.pattern, args.recursive, args.dry_run)
    if args.retention_days > 0:
        prune(args.dest, args.retention_days, args.dry_run)

if __name__ == "__main__":
    main()
