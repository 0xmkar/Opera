#!/usr/bin/env bash
# Snapshot all local work onto save-work-locally before destructive git operations.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${SAVE_WORK_BRANCH:-save-work-locally}"
TAG_PREFIX="${SAVE_WORK_TAG_PREFIX:-saved-work}"

cd "$ROOT"

if git diff-index --quiet HEAD -- && git diff-index --quiet --cached HEAD --; then
  untracked="$(git ls-files --others --exclude-standard)"
  if [[ -z "$untracked" ]]; then
    echo "Nothing to save — working tree is clean."
    exit 0
  fi
fi

current="$(git branch --show-current)"
if [[ "$current" != "$BRANCH" ]]; then
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git checkout "$BRANCH"
  else
    git checkout -b "$BRANCH"
  fi
fi

echo "Staging changes ( .env is never committed )..."
git add -A
if git diff-index --quiet --cached HEAD --; then
  echo "Nothing staged after git add -A."
  exit 0
fi

msg="${SAVE_WORK_MESSAGE:-WIP: save local changes $(date +%Y-%m-%d)}"
git commit -m "$msg"

tag="${TAG_PREFIX}-$(date +%Y%m%d-%H%M%S)"
git tag "$tag"

echo ""
echo "Saved on branch: $BRANCH"
echo "Tag:             $tag"
echo "Commit:          $(git rev-parse --short HEAD)"
echo ""
echo "Restore later with:"
echo "  git checkout $BRANCH"
echo "  # or: git checkout $tag"
echo ""
echo "Safe to run history rewrite on main after switching back:"
echo "  git checkout main"
