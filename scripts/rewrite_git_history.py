#!/usr/bin/env python3
"""
Squash git history to ~40 feature commits with meaningful messages and your authorship.

Default mode groups real work into feature-sized commits (e.g. challenge trading,
Polymarket, team missions) instead of hundreds of generic "update frontend" commits.

Save uncommitted work FIRST:
  bash scripts/save_local_work.sh

Usage:
  python3 scripts/rewrite_git_history.py
  python3 scripts/rewrite_git_history.py --apply
  python3 scripts/rewrite_git_history.py --target-commits 40 --apply
  python3 scripts/rewrite_git_history.py --preserve-all-commits --apply
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_FILENAME = ".git-rewrite-commit-map.json"
# Tracked paths left untouched by --stash (still in your working tree).
DEFAULT_STASH_KEEP = (".gitignore",)


def run_git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}):\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def git_config(key: str) -> str | None:
    try:
        value = run_git("config", "--get", key)
        return value or None
    except RuntimeError:
        return None


def is_merge_commit(commit: str) -> bool:
    try:
        run_git("rev-parse", "--verify", f"{commit}^2")
        return True
    except RuntimeError:
        return False


def changed_files(commit: str) -> list[str]:
    out = run_git("diff-tree", "--no-commit-id", "--name-status", "-r", commit)
    files: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append(parts[-1])
    return files


def file_statuses(commit: str) -> list[tuple[str, str]]:
    out = run_git("diff-tree", "--no-commit-id", "--name-status", "-r", commit)
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status, path = parts[0], parts[-1]
            rows.append((status, path))
    return rows


def diff_stat(commit: str) -> tuple[int, int]:
    out = run_git("show", "--numstat", "--format=", commit)
    added = deleted = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            added += int(parts[0]) if parts[0] != "-" else 0
            deleted += int(parts[1]) if parts[1] != "-" else 0
        except ValueError:
            continue
    return added, deleted


def basename_words(path: str) -> list[str]:
    stem = Path(path).stem.replace("_", " ").replace("-", " ")
    words = re.findall(r"[a-zA-Z]{3,}", stem)
    return [w.lower() for w in words if w.lower() not in {"tsx", "jsx", "test", "tests"}]


def dominant_area(paths: list[str]) -> str | None:
    area_counts: Counter[str] = Counter()
    for path in paths:
        parts = path.split("/")
        if not parts:
            continue
        if parts[0] == "service" and len(parts) > 1:
            area_counts[f"service/{parts[1]}"] += 1
        elif parts[0] in {"docs", "research", "skills", "scripts"}:
            area_counts[parts[0]] += 1
        else:
            area_counts[parts[0]] += 1
    if not area_counts:
        return None
    return area_counts.most_common(1)[0][0]


def topic_from_paths(paths: list[str]) -> str | None:
    joined = " ".join(paths).lower()
    topics = [
        ("polymarket", "Polymarket integration"),
        ("challenge", "challenge trading"),
        ("leaderboard", "leaderboard"),
        ("experiment", "experiment metrics"),
        ("copytrade", "copy trading"),
        ("signal", "signal quality"),
        ("frontend", "frontend UI"),
        ("migrate", "database migration"),
        ("postgres", "Postgres support"),
        ("sqlite", "SQLite storage"),
        ("i18n", "internationalization"),
        ("openapi", "API documentation"),
        ("worker", "background worker"),
        ("price", "price fetching"),
        ("trade", "trade execution"),
        ("agent", "agent management"),
        ("team", "team missions"),
        ("reward", "rewards"),
        ("permission", "permissions"),
        ("heartbeat", "agent heartbeat"),
        ("market-intel", "market intelligence"),
    ]
    for needle, label in topics:
        if needle in joined:
            return label
    return None


def action_from_statuses(rows: list[tuple[str, str]]) -> str:
    statuses = {status[0] for status, _ in rows}
    if statuses <= {"A"}:
        return "Add"
    if statuses <= {"D"}:
        return "Remove"
    if any(s.startswith("R") for s in statuses):
        return "Rename"
    if "M" in statuses and not any(s in {"A", "D"} for s in statuses):
        return "Update"
    if "A" in statuses:
        return "Add"
    if "D" in statuses:
        return "Remove"
    return "Update"


def commit_prefix(paths: list[str], added: int, deleted: int, original: str) -> str:
    lower_orig = original.lower()
    if lower_orig.startswith("fix") or "fix" in lower_orig:
        return "fix"
    if any(p.endswith(".md") for p in paths) and all(
        p.endswith((".md", ".txt", ".rst")) or "/docs/" in p for p in paths
    ):
        return "docs"
    if any("test" in p for p in paths):
        return "test"
    if deleted > added * 2 and added < 20:
        return "chore"
    return "feat"


def shorten_subject(text: str, limit: int = 72) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def describe_primary_files(paths: list[str], limit: int = 2) -> str:
    scored: list[tuple[int, str]] = []
    for path in paths:
        depth_penalty = path.count("/")
        name_bonus = len(basename_words(path))
        scored.append((depth_penalty - name_bonus, path))
    scored.sort()
    chosen = [Path(p).name for _, p in scored[:limit]]
    readable = ", ".join(chosen)
    return readable


def generate_message(commit: str, original: str) -> str:
    if is_merge_commit(commit):
        return "Merge branch updates"

    rows = file_statuses(commit)
    paths = [path for _, path in rows]
    if not paths:
        cleaned = re.sub(r"\s+#\d+\s*$", "", original).strip()
        if cleaned and not cleaned.lower().startswith("merge"):
            vague = cleaned.lower() in {
                "init update",
                "update",
                "update data",
                "update frontend",
                "wip",
                "fix",
                "changes",
            }
            if not vague:
                return shorten_subject(cleaned)
        return "chore: initial project setup" if "init" in original.lower() else "chore: repository maintenance"

    added, deleted = diff_stat(commit)
    prefix = commit_prefix(paths, added, deleted, original)
    action = action_from_statuses(rows)
    topic = topic_from_paths(paths)
    area = dominant_area(paths)

    if topic:
        subject = f"{action.lower()} {topic}"
    elif area:
        subject = f"{action.lower()} {area.replace('/', ' ')}"
    else:
        subject = f"{action.lower()} {describe_primary_files(paths)}"

    subject = subject[0].upper() + subject[1:]
    message = f"{prefix}: {subject}"

    if len(paths) == 1:
        return shorten_subject(message)

    if len(paths) <= 4:
        extras = ", ".join(Path(p).name for p in paths[:3])
        if len(paths) > 3:
            extras += f" (+{len(paths) - 3} more)"
        body = f"\n\nTouches: {extras}"
        return shorten_subject(message) + body

    return shorten_subject(message) + f"\n\nTouches {len(paths)} files"


def assign_dates(commits: list[str], days: int, tz: tzinfo) -> dict[str, str]:
    if not commits:
        return {}

    end = datetime.now(tz)
    start = end - timedelta(days=days)
    span_seconds = max((end - start).total_seconds(), 1.0)
    n = len(commits)

    # Deterministic jitter so previews are stable across runs.
    rng = random.Random(42)
    dates: dict[str, str] = {}
    previous: datetime | None = None

    for index, commit in enumerate(commits):
        frac = index / max(n - 1, 1)
        base = start + timedelta(seconds=span_seconds * frac)

        hour = 9 + int(frac * 11)  # 09:00 – 20:00
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        candidate = base.replace(hour=hour, minute=minute, second=second, microsecond=0)

        if previous and candidate <= previous:
            candidate = previous + timedelta(minutes=rng.randint(3, 25))

        if candidate > end:
            candidate = end - timedelta(minutes=max(n - index, 1))

        dates[commit] = candidate.strftime("%Y-%m-%d %H:%M:%S %z")
        previous = candidate

    return dates


def collect_commits() -> list[str]:
    out = run_git("rev-list", "--reverse", "HEAD")
    return [line for line in out.splitlines() if line.strip()]


def build_commit_map(
    commits: list[str],
    author_name: str,
    author_email: str,
    days: int,
    tz: tzinfo,
) -> dict[str, dict[str, str]]:
    dates = assign_dates(commits, days, tz)
    mapping: dict[str, dict[str, str]] = {}
    for commit in commits:
        original = run_git("log", "-1", "--format=%s", commit)
        mapping[commit] = {
            "author_name": author_name,
            "author_email": author_email,
            "date": dates[commit],
            "message": generate_message(commit, original),
            "original_message": original,
            "original_author": run_git("log", "-1", "--format=%an <%ae>", commit),
        }
    return mapping


def print_preview(mapping: dict[str, dict[str, str]], limit: int) -> None:
    commits = list(mapping.keys())
    print(f"Would rewrite {len(commits)} commits.\n")
    print("First commits:")
    for commit in commits[:limit]:
        entry = mapping[commit]
        print(f"  {commit[:10]}  {entry['date']}")
        print(f"    was: {entry['original_author']} — {entry['original_message']}")
        print(f"    new: {entry['author_name']} — {entry['message'].splitlines()[0]}")
        print()
    if len(commits) > limit * 2:
        print("  ...\n")
    print("Last commits:")
    for commit in commits[-limit:]:
        entry = mapping[commit]
        print(f"  {commit[:10]}  {entry['date']}")
        print(f"    was: {entry['original_author']} — {entry['original_message']}")
        print(f"    new: {entry['author_name']} — {entry['message'].splitlines()[0]}")
        print()


def changed_tracked_paths() -> list[str]:
    unstaged = run_git("diff-index", "--name-only", "HEAD", "--").splitlines()
    staged = run_git("diff-index", "--cached", "--name-only", "HEAD", "--").splitlines()
    return sorted(set(unstaged + staged))


def worktree_dirty(keep_paths: tuple[str, ...] = ()) -> bool:
    """True when tracked files outside keep_paths differ from HEAD."""
    keep = set(keep_paths)
    return any(path not in keep for path in changed_tracked_paths())


def save_keep_paths(keep_paths: tuple[str, ...]) -> dict[str, str]:
    saved: dict[str, str] = {}
    for path in keep_paths:
        if path not in changed_tracked_paths():
            continue
        full = ROOT / path
        if full.is_file():
            saved[path] = full.read_text(encoding="utf-8")
    return saved


def restore_keep_paths(saved: dict[str, str]) -> None:
    for path, content in saved.items():
        (ROOT / path).write_text(content, encoding="utf-8")


def reset_keep_paths_for_rewrite(keep_paths: tuple[str, ...]) -> None:
    """filter-branch needs a clean index; temporarily revert kept files."""
    for path in keep_paths:
        if path in changed_tracked_paths():
            run_git("restore", "--source=HEAD", "--staged", "--worktree", "--", path)


def require_clean_worktree(auto_stash: bool, keep_paths: tuple[str, ...]) -> tuple[bool, dict[str, str]]:
    """Return (did_stash, saved keep-path contents to restore after rewrite)."""
    saved_keep = save_keep_paths(keep_paths)
    dirty_outside_keep = worktree_dirty(keep_paths)

    if not dirty_outside_keep and not saved_keep:
        return False, {}

    if not auto_stash:
        kept = ", ".join(keep_paths) if keep_paths else "(none)"
        print(
            "Error: working tree has uncommitted changes.\n"
            "  git filter-branch requires a clean tree.\n"
            f"  Kept locally (not stashed): {kept}\n"
            "  Options:\n"
            "    1. Commit or stash your other changes manually, then re-run --apply\n"
            "    2. Re-run with --stash to auto-stash other changes and restore after",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if dirty_outside_keep:
        print("Stashing uncommitted changes (excluding kept paths)...")
        if keep_paths:
            excludes = [f":!{path}" for path in keep_paths]
            run_git(
                "stash",
                "push",
                "-u",
                "-m",
                "rewrite_git_history auto-stash (restore with: git stash pop)",
                "--",
                ".",
                *excludes,
            )
        else:
            run_git(
                "stash",
                "push",
                "-u",
                "-m",
                "rewrite_git_history auto-stash (restore with: git stash pop)",
            )
    else:
        print("Keeping local edits to:", ", ".join(keep_paths))

    if saved_keep:
        reset_keep_paths_for_rewrite(keep_paths)

    return dirty_outside_keep, saved_keep


def restore_stash(did_stash: bool) -> None:
    if not did_stash:
        return
    print("Restoring stashed changes...")
    run_git("stash", "pop")


def create_backup_branch() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"backup/pre-rewrite-{stamp}"
    run_git("branch", branch)
    return branch


def write_map_file(mapping: dict[str, dict[str, str]]) -> Path:
    path = ROOT / MAP_FILENAME
    path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    return path


def write_filter_helpers(map_path: Path) -> tuple[Path, Path]:
    env_filter = ROOT / ".git-rewrite-env-filter.sh"
    msg_filter = ROOT / ".git-rewrite-msg-filter.sh"
    map_file = str(map_path)

    env_filter.write_text(
        f"""#!/bin/sh
eval "$(python3 - <<'PY'
import json, os
commit = os.environ.get("GIT_COMMIT", "")
mapping = json.load(open({map_file!r}))
entry = mapping.get(commit)
if not entry:
    raise SystemExit(0)
name = entry["author_name"]
email = entry["author_email"]
date = entry["date"]
print(f'export GIT_AUTHOR_NAME={{name!r}}')
print(f'export GIT_AUTHOR_EMAIL={{email!r}}')
print(f'export GIT_AUTHOR_DATE={{date!r}}')
print(f'export GIT_COMMITTER_NAME={{name!r}}')
print(f'export GIT_COMMITTER_EMAIL={{email!r}}')
print(f'export GIT_COMMITTER_DATE={{date!r}}')
PY
)"
""",
        encoding="utf-8",
    )

    msg_filter.write_text(
        f"""#!/bin/sh
python3 - <<'PY'
import json, os, sys
commit = os.environ.get("GIT_COMMIT", "")
mapping = json.load(open({map_file!r}))
entry = mapping.get(commit)
if entry:
    sys.stdout.write(entry["message"])
else:
    sys.stdout.write(sys.stdin.read())
PY
""",
        encoding="utf-8",
    )

    env_filter.chmod(0o755)
    msg_filter.chmod(0o755)
    return env_filter, msg_filter


def apply_rewrite(map_path: Path, all_branches: bool) -> None:
    env_filter, msg_filter = write_filter_helpers(map_path)

    print("Running git filter-branch (this may take a minute)...")
    env = os.environ.copy()
    env["FILTER_BRANCH_SQUELCH_WARNING"] = "1"
    rewrite_target = ["--", "--all"] if all_branches else ["HEAD"]
    result = subprocess.run(
        [
            "git",
            "filter-branch",
            "-f",
            "--env-filter",
            f". {env_filter}",
            "--msg-filter",
            str(msg_filter),
            *rewrite_target,
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "git filter-branch failed"
            + (f":\n{detail}" if detail else "")
        )

    for ref in ROOT.glob("refs/original/**"):
        pass  # refs preserved by filter-branch

    print("Expiring reflog and running garbage collection...")
    subprocess.run(["git", "for-each-ref", "--format=%(refname)", "refs/original/"],
                   cwd=ROOT, capture_output=True, text=True, check=False)
    original_refs = run_git("for-each-ref", "--format=%(refname)", "refs/original/")
    for ref in original_refs.splitlines():
        if ref.strip():
            subprocess.run(["git", "update-ref", "-d", ref.strip()], cwd=ROOT, check=False)
    subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"], cwd=ROOT, check=False)
    subprocess.run(["git", "gc", "--prune=now"], cwd=ROOT, check=False)


def cleanup_helpers() -> None:
    for name in (
        MAP_FILENAME,
        ".git-rewrite-env-filter.sh",
        ".git-rewrite-msg-filter.sh",
    ):
        path = ROOT / name
        if path.exists():
            path.unlink()


@dataclass
class PlannedCommit:
    message: str
    paths: list[str] = field(default_factory=list)
    date: str = ""
    source_commits: list[str] = field(default_factory=list)


def is_generic_message(message: str) -> bool:
    cleaned = re.sub(r"\s+#\d+\s*$", "", message).strip().lower()
    if not cleaned or cleaned.startswith("merge"):
        return True
    if cleaned in {
        "update",
        "fix",
        "changes",
        "wip",
        "init update",
        "update data",
        "update frontend",
        "chore: repository maintenance",
    }:
        return True
    if re.match(r"^update \w+$", cleaned):
        return True
    if re.match(r"^(feat|fix|chore|docs|test): (add|update|remove) ", cleaned):
        tail = cleaned.split(": ", 1)[-1]
        if len(tail.split()) <= 4:
            return True
    return False


def normalize_message(message: str) -> str:
    msg = re.sub(r"\s+#\d+\s*$", "", message).strip()
    msg = re.sub(r"\s+", " ", msg)
    if re.match(r"^(feat|fix|docs|chore|test|refactor):", msg, re.I):
        return shorten_subject(msg)
    lower = msg.lower()
    if lower.startswith(("add ", "enable ", "guard ", "allow ", "expose ", "document ")):
        return shorten_subject(f"feat: {msg}")
    if lower.startswith(("fix ", "repair ", "guard ")):
        return shorten_subject(f"fix: {msg}")
    if lower.startswith("docs"):
        return shorten_subject(f"docs: {msg}")
    return shorten_subject(f"feat: {msg}")


def score_message(message: str) -> int:
    if is_generic_message(message):
        return -100
    score = min(len(message), 90)
    if re.search(r"\b(add|enable|support|integration|challenge|polymarket|leaderboard)\b", message, re.I):
        score += 25
    if message[:1].isupper():
        score += 5
    return score


def commit_feature_key(commit: str) -> str:
    paths = changed_files(commit)
    topic = topic_from_paths(paths)
    if topic:
        return topic
    area = dominant_area(paths)
    if area:
        return area.replace("/", "-")
    if paths:
        top = paths[0].split("/")[0]
        return top
    original = run_git("log", "-1", "--format=%s", commit).lower()
    for word in ("challenge", "polymarket", "leaderboard", "experiment", "team", "signal", "trade"):
        if word in original:
            return word
    return "platform-core"


def collect_non_merge_commits() -> list[str]:
    out = run_git("rev-list", "--reverse", "--no-merges", "HEAD")
    return [line for line in out.splitlines() if line.strip()]


def merge_smallest_groups(groups: list[list[str]], target: int) -> list[list[str]]:
    merged = [list(g) for g in groups]
    while len(merged) > target:
        pair_idx = min(
            range(len(merged) - 1),
            key=lambda i: len(merged[i]) + len(merged[i + 1]),
        )
        merged[pair_idx] = merged[pair_idx] + merged.pop(pair_idx + 1)
    return merged


def split_largest_groups(groups: list[list[str]], target: int) -> list[list[str]]:
    split = [list(g) for g in groups]
    while len(split) < target:
        idx = max(range(len(split)), key=lambda i: len(split[i]))
        if len(split[idx]) < 2:
            break
        mid = len(split[idx]) // 2
        chunk = split.pop(idx)
        split[idx:idx] = [chunk[:mid], chunk[mid:]]
    return split


def cluster_commits(commits: list[str], target: int) -> list[list[str]]:
    buckets: dict[str, list[str]] = {}
    order: list[str] = []
    for commit in commits:
        key = commit_feature_key(commit)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(commit)

    groups = [buckets[key] for key in order]
    if len(groups) > target:
        groups = merge_smallest_groups(groups, target)
    elif len(groups) < target:
        groups = split_largest_groups(groups, target)
    return groups


def message_for_group(group: list[str]) -> str:
    best_score = -1
    best_message = ""
    for commit in group:
        original = run_git("log", "-1", "--format=%s", commit)
        score = score_message(original)
        if score > best_score:
            best_score = score
            best_message = original
    if best_score > 0:
        return normalize_message(best_message)

    paths: list[str] = []
    for commit in group:
        paths.extend(changed_files(commit))
    paths = sorted(set(paths))
    synthetic = generate_message(group[-1], "feature update")
    return normalize_message(synthetic.split(":", 1)[-1].strip() if ":" in synthetic else synthetic)


def assign_files_to_groups(
    head_files: list[str],
    groups: list[list[str]],
) -> list[list[str]]:
    touch: Counter[tuple[int, str]] = Counter()
    for gidx, group in enumerate(groups):
        for commit in group:
            for path in changed_files(commit):
                touch[(gidx, path)] += 1

    per_group: list[list[str]] = [[] for _ in groups]
    for path in head_files:
        scores = [(touch.get((i, path), 0), i) for i in range(len(groups))]
        best = max(scores)[1]
        if touch.get((best, path), 0) == 0:
            best = len(groups) - 1
        per_group[best].append(path)

    assigned = {p for chunk in per_group for p in chunk}
    missing = [p for p in head_files if p not in assigned]
    if missing:
        per_group[-1].extend(missing)
    return per_group


EXCLUDE_MESSAGE_RE = re.compile(
    r"save-work|rewrite_git|auto-stash|\bwip\b|narrow scripts gitignore",
    re.I,
)

FILE_BUCKET_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "bootstrap",
        "feat: Bootstrap Opera agent-native trading platform",
        ("README.md", ".gitignore", ".env.example", "package-lock.json", "tsconfig.json"),
    ),
    ("docs", "docs: Add platform, API, and operator documentation", ("docs/",)),
    (
        "skills",
        "feat: Add agent skill pack for Opera, trading, and market intel",
        ("skills/",),
    ),
    (
        "local-fleet",
        "feat: Add local agent fleet runners and seed tooling",
        ("scripts/local-fleet/", "scripts/save_local_work", "scripts/strip_chinese"),
    ),
    (
        "server-core",
        "feat: Add FastAPI server core, routing, and worker",
        (
            "service/server/main.py",
            "service/server/config.py",
            "service/server/routes.py",
            "service/server/routes_shared.py",
            "service/server/utils.py",
            "service/server/worker.py",
            "service/requirements.txt",
        ),
    ),
    (
        "database",
        "feat: Add database layer with SQLite and Postgres migration",
        ("service/server/database.py", "migrate_sqlite", "test_database_adapter"),
    ),
    (
        "agents",
        "feat: Add agent registration, auth, and permissions",
        ("routes_agent", "routes_auth", "permissions.py"),
    ),
    (
        "signals",
        "feat: Add signals, replies, and market intelligence feeds",
        ("routes_signals", "signal_quality", "market_intel"),
    ),
    (
        "trading",
        "feat: Add trade execution, copy trading, and price fetching",
        ("routes_trading", "price_fetcher", "routes_copytrade"),
    ),
    (
        "challenges",
        "feat: Add challenge trading, tournaments, and leaderboards",
        ("challenge", "monthly_challenges", "ChallengePage"),
    ),
    ("polymarket", "feat: Add Polymarket paper trading integration", ("polymarket",)),
    (
        "experiments",
        "feat: Add experiment metrics and research admin tooling",
        ("experiment", "ExperimentAdmin", "ResearchExports"),
    ),
    (
        "teams",
        "feat: Add team missions and cooperation challenges",
        ("team", "TeamMissions"),
    ),
    (
        "leaderboard",
        "feat: Add leaderboard, drawdown charts, and rankings UI",
        ("leaderboard", "drawdown", "AppPages"),
    ),
    (
        "frontend-shell",
        "feat: Add React frontend shell, routing, and chrome",
        (
            "App.tsx",
            "appChrome",
            "appShared",
            "appCommunity",
            "index.html",
            "service/frontend/package.json",
        ),
    ),
    ("i18n", "feat: Simplify frontend copy and localization", ("i18n.ts",)),
    ("tasks", "feat: Add background tasks for prices and settlements", ("tasks.py",)),
    (
        "research",
        "feat: Add research exports, schemas, and analysis pipeline",
        ("research/",),
    ),
    (
        "server-scripts",
        "feat: Add server maintenance and data repair scripts",
        ("service/server/scripts/",),
    ),
    ("tests", "test: Add API and database integration tests", ("service/server/tests/",)),
]


def bucket_for_path(path: str) -> str:
    lower = path.lower()
    for bucket_id, _message, patterns in FILE_BUCKET_RULES:
        for pattern in patterns:
            pat = pattern.lower()
            if pat.endswith("/") and lower.startswith(pat):
                return bucket_id
            if pat in lower or lower.endswith(pat) or lower.split("/")[-1] == pat:
                return bucket_id
    if lower.startswith("service/frontend/"):
        return "frontend-shell"
    if lower.startswith("service/server/"):
        return "server-core"
    return "bootstrap"


def bucket_message_lookup() -> dict[str, str]:
    return {bucket_id: message for bucket_id, message, _ in FILE_BUCKET_RULES}


def history_commit_pool() -> list[str]:
    try:
        backups = [
            line.strip().lstrip("* ")
            for line in run_git("branch", "--list", "backup/pre-rewrite-*").splitlines()
            if line.strip()
        ]
        if backups:
            ref = backups[-1].split()[-1]
            out = run_git("rev-list", "--reverse", "--no-merges", ref)
            return [line for line in out.splitlines() if line.strip()]
    except RuntimeError:
        pass
    return collect_non_merge_commits()


def merge_bucket_items(
    items: list[tuple[str, str, list[str]]],
    target: int,
) -> list[tuple[str, str, list[str]]]:
    merged = [(bid, msg, list(paths)) for bid, msg, paths in items if paths]
    while len(merged) > target:
        idx = min(
            range(len(merged) - 1),
            key=lambda i: len(merged[i][2]) + len(merged[i + 1][2]),
        )
        left_id, left_msg, left_paths = merged[idx]
        _right_id, _right_msg, right_paths = merged[idx + 1]
        merged[idx : idx + 2] = [(left_id, left_msg, left_paths + right_paths)]
    while len(merged) < target:
        idx = max(range(len(merged)), key=lambda i: len(merged[i][2]))
        paths = merged[idx][2]
        if len(paths) < 2:
            break
        mid = len(paths) // 2
        bucket_id, message, _paths = merged[idx]
        merged[idx : idx + 1] = [
            (bucket_id, message, paths[:mid]),
            (bucket_id, message, paths[mid:]),
        ]
    return merged


def message_for_paths(
    paths: list[str],
    commits: list[str],
    bucket_id: str,
    default_message: str,
    part_index: int,
) -> str:
    if part_index > 0:
        topic = topic_from_paths(paths)
        if topic:
            return normalize_message(f"Extend {topic}")
        return normalize_message(f"{default_message} (part {part_index + 1})")

    path_set = set(paths)
    best_score = 0
    best_message = ""
    for commit in commits:
        original = run_git("log", "-1", "--format=%s", commit)
        if EXCLUDE_MESSAGE_RE.search(original):
            continue
        overlap = len(path_set.intersection(changed_files(commit)))
        if overlap == 0:
            continue
        score = score_message(original) + overlap * 8
        if score > best_score:
            best_score = score
            best_message = original
    if best_score >= 25:
        return normalize_message(best_message)
    return normalize_message(default_message)


def build_squash_plan(
    target: int,
    author_name: str,
    author_email: str,
    days: int,
    tz: tzinfo,
) -> list[PlannedCommit]:
    del author_name, author_email  # used at commit time
    head_files = run_git("ls-files").splitlines()
    commits = history_commit_pool()
    messages = bucket_message_lookup()

    bucket_files: dict[str, list[str]] = {}
    bucket_order: list[str] = []
    for path in head_files:
        bucket = bucket_for_path(path)
        if bucket not in bucket_files:
            bucket_files[bucket] = []
            bucket_order.append(bucket)
        bucket_files[bucket].append(path)

    items: list[tuple[str, str, list[str]]] = []
    for bucket_id in bucket_order:
        default = messages.get(bucket_id, f"feat: Add {bucket_id.replace('-', ' ')}")
        items.append((bucket_id, default, bucket_files[bucket_id]))

    items = merge_bucket_items(items, target)

    date_keys = [f"p{i}" for i in range(len(items))]
    dates = assign_dates(date_keys, days, tz)

    part_counts: Counter[str] = Counter()
    planned: list[PlannedCommit] = []
    for idx, (bucket_id, default_message, paths) in enumerate(items):
        part_index = part_counts[bucket_id]
        part_counts[bucket_id] += 1
        planned.append(
            PlannedCommit(
                message=message_for_paths(
                    paths, commits, bucket_id, default_message, part_index
                ),
                paths=sorted(paths),
                date=dates[f"p{idx}"],
            )
        )
    return planned


def print_squash_preview(plan: list[PlannedCommit], limit: int) -> None:
    original = len(collect_non_merge_commits())
    print(f"Would create {len(plan)} feature commits (squashed from {original} original).\n")
    if len(plan) <= limit * 2:
        show = plan
    else:
        show = plan[:limit] + plan[-limit:]
        print(f"  ... ({len(plan) - limit * 2} commits omitted) ...\n")
    for item in show:
        print(f"  {item.date}  {item.message}")
        print(f"    {len(item.paths)} files")
        print()


def checkout_paths_from(ref: str, paths: list[str], batch_size: int = 60) -> None:
    for offset in range(0, len(paths), batch_size):
        batch = paths[offset : offset + batch_size]
        run_git("checkout", ref, "--", *batch)


def git_commit_with_identity(message: str, when: str, name: str, email: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_AUTHOR_DATE": when,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_COMMITTER_DATE": when,
        }
    )
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git commit failed: {detail}")


def apply_squash_rewrite(
    plan: list[PlannedCommit],
    source_ref: str,
    branch: str,
    author_name: str,
    author_email: str,
) -> None:
    if not plan:
        raise RuntimeError("No commits in squash plan")

    print(f"Rebuilding history as {len(plan)} commits on orphan branch...")
    run_git("checkout", "--orphan", "_history_rewrite")
    subprocess.run(
        ["git", "rm", "-rf", "--ignore-unmatch", "."],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )

    for item in plan:
        checkout_paths_from(source_ref, item.paths)
        run_git("add", "-A")
        if subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=ROOT,
            capture_output=True,
        ).returncode == 0:
            continue
        git_commit_with_identity(item.message, item.date, author_name, author_email)

    diff = subprocess.run(
        ["git", "diff", "--stat", source_ref, "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if diff.stdout.strip():
        raise RuntimeError(
            "Squashed tree does not match source — aborting.\n" + diff.stdout[:500]
        )

    run_git("branch", "-f", branch)
    run_git("checkout", branch)
    subprocess.run(["git", "branch", "-D", "_history_rewrite"], cwd=ROOT, check=False)
    subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"], cwd=ROOT, check=False)
    subprocess.run(["git", "gc", "--prune=now"], cwd=ROOT, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rewrite git history: your authorship, last N days, better messages.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rewrite history (default is dry-run preview only)",
    )
    parser.add_argument(
        "--author-name",
        default=git_config("user.name"),
        help="Author name for rewritten commits (default: git user.name)",
    )
    parser.add_argument(
        "--author-email",
        default=git_config("user.email"),
        help="Author email for rewritten commits (default: git user.email)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Spread commit dates across this many days (default: 14)",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=5,
        help="How many commits to show at start/end in preview mode",
    )
    parser.add_argument(
        "--export-map",
        type=Path,
        help="Write the commit map JSON to this path and exit",
    )
    parser.add_argument(
        "--all-branches",
        action="store_true",
        help="Rewrite every local branch (default: current branch only)",
    )
    parser.add_argument(
        "--stash",
        action="store_true",
        help="Auto-stash uncommitted changes before rewrite, restore after",
    )
    parser.add_argument(
        "--stash-keep",
        action="append",
        default=[],
        metavar="PATH",
        help="Do not stash these paths; keep local edits (default: .gitignore)",
    )
    parser.add_argument(
        "--target-commits",
        type=int,
        default=40,
        help="Squash history to about this many feature commits (default: 40)",
    )
    parser.add_argument(
        "--preserve-all-commits",
        action="store_true",
        help="Keep every commit (old 1:1 filter-branch mode, not recommended)",
    )
    return parser.parse_args()


def resolve_stash_keep(extra_keep: list[str]) -> tuple[str, ...]:
    keep = list(DEFAULT_STASH_KEEP)
    for path in extra_keep:
        if path not in keep:
            keep.append(path)
    return tuple(keep)


def main() -> int:
    args = parse_args()

    if not args.author_name or not args.author_email:
        print(
            "Missing author identity. Set git user.name/user.email or pass "
            "--author-name / --author-email.",
            file=sys.stderr,
        )
        return 1

    if args.days < 1:
        print("--days must be at least 1", file=sys.stderr)
        return 1

    if args.target_commits < 2 and not args.preserve_all_commits:
        print("--target-commits must be at least 2", file=sys.stderr)
        return 1

    tz = datetime.now().astimezone().tzinfo
    if tz is None:
        raise RuntimeError("Could not determine local timezone")

    stash_keep = resolve_stash_keep(args.stash_keep)
    use_squash = not args.preserve_all_commits

    try:
        if use_squash:
            plan = build_squash_plan(
                target=args.target_commits,
                author_name=args.author_name,
                author_email=args.author_email,
                days=args.days,
                tz=tz,
            )
        else:
            commits = collect_commits()
            mapping = build_commit_map(
                commits,
                author_name=args.author_name,
                author_email=args.author_email,
                days=args.days,
                tz=tz,
            )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.export_map:
        if use_squash:
            payload = [
                {
                    "message": p.message,
                    "date": p.date,
                    "paths": p.paths,
                    "source_commits": p.source_commits,
                }
                for p in plan
            ]
            args.export_map.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            args.export_map.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
        print(f"Wrote commit map to {args.export_map}")
        return 0

    if args.apply:
        did_stash, saved_keep = require_clean_worktree(
            auto_stash=args.stash, keep_paths=stash_keep
        )
    else:
        did_stash = False
        saved_keep = {}
        if worktree_dirty(stash_keep):
            kept = ", ".join(stash_keep)
            print(
                f"Note: you have uncommitted tracked changes outside {kept}; "
                "--apply will require a clean tree (or pass --stash).",
            )
        elif save_keep_paths(stash_keep):
            print(f"Note: local edits to {', '.join(stash_keep)} are kept when using --stash.")

    if use_squash:
        print_squash_preview(plan, args.preview)
    else:
        print_preview(mapping, args.preview)

    if not args.apply:
        print("Dry run only. Re-run with --apply to rewrite history.")
        print("Optional: --export-map rewrite-map.json to inspect the full plan.")
        return 0

    backup = create_backup_branch()
    print(f"Created backup branch: {backup}")

    source_ref = run_git("rev-parse", "HEAD")
    branch = run_git("branch", "--show-current")

    try:
        if use_squash:
            apply_squash_rewrite(
                plan,
                source_ref=source_ref,
                branch=branch,
                author_name=args.author_name,
                author_email=args.author_email,
            )
        else:
            map_path = write_map_file(mapping)
            apply_rewrite(map_path, all_branches=args.all_branches)
    except RuntimeError as exc:
        if did_stash:
            print("Rewrite failed; your changes are still in git stash.", file=sys.stderr)
        if saved_keep:
            restore_keep_paths(saved_keep)
        print(exc, file=sys.stderr)
        try:
            run_git("checkout", branch)
        except RuntimeError:
            pass
        return 1
    finally:
        cleanup_helpers()

    restore_stash(did_stash)
    if saved_keep:
        restore_keep_paths(saved_keep)

    print()
    print("Done. History rewritten.")
    print(f"  Backup branch : {backup}")
    print(f"  Author        : {args.author_name} <{args.author_email}>")
    print(f"  Date window   : last {args.days} days")
    if use_squash:
        print(f"  Commits       : {len(plan)} feature commits")
    print("  Verify with     : git log --oneline --format='%h %ad %s' --date=short")
    print()
    print("If this repo has a remote, you will need a force push:")
    print("  git push --force-with-lease")
    print()
    print("Only force-push if you own the repo or have coordinated with collaborators.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
