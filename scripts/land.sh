#!/usr/bin/env bash
#
# land.sh — integrate a task worktree's commits into main, cleanly and linearly.
#
# Run from the MAIN worktree (the primary checkout, on `main`) after committing your
# work in a task worktree:
#
#     scripts/land.sh <task-branch>
#
# What it does (low-overhead, clean-or-refuse — never a half-merge):
#   1. Sync local `main` with `origin/main` (fast-forward only).
#   2. Fast-forward `main` up to <task-branch>'s commits — keeps history LINEAR (no
#      merge bubble). Merging reads the branch; it does not check it out, so this
#      works while the branch is still checked out in its worktree.
#   3. Push `main` to origin, so `main` ≡ `origin/main`.
#   4. Remove the task worktree and delete the branch.
#
# If `main` moved and step 2 can't fast-forward, it STOPS and prints the exact rebase
# command to run in the task worktree; rebase there, then re-run land. Nothing is left
# half-merged or stranded.
set -euo pipefail

branch="${1:-}"
if [ -z "$branch" ]; then
  echo "usage: scripts/land.sh <task-branch>" >&2
  exit 2
fi

cur="$(git symbolic-ref --short HEAD 2>/dev/null || true)"
if [ "$cur" != "main" ]; then
  echo "refuse: run land from the main worktree (HEAD is on '$cur', not 'main')." >&2
  echo "        cd to the primary checkout, then: scripts/land.sh $branch" >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "refuse: the main worktree has uncommitted changes — commit or stash them first." >&2
  exit 1
fi
if ! git show-ref --verify --quiet "refs/heads/$branch"; then
  echo "refuse: branch '$branch' does not exist." >&2
  exit 1
fi

task_wt="$(git worktree list --porcelain | awk -v b="refs/heads/$branch" '/^worktree /{w=$2} $0=="branch "b{print w}')"

echo "→ syncing main with origin…"
git fetch origin
git merge --ff-only origin/main

echo "→ fast-forwarding main to '$branch'…"
if ! git merge --ff-only "$branch"; then
  echo >&2
  echo "Cannot fast-forward — main has advanced since '$branch' was created." >&2
  echo "Rebase the task branch onto the latest main in its worktree, then re-run land:" >&2
  echo "    ( cd '${task_wt:-<task-worktree>}' && git fetch origin && git rebase origin/main )   # resolve any conflicts here" >&2
  echo "    scripts/land.sh $branch" >&2
  exit 1
fi

echo "→ pushing main…"
git push origin main

echo "→ removing worktree + branch…"
if [ -n "$task_wt" ]; then
  git worktree remove "$task_wt"
fi
git branch -d "$branch"

echo "✓ landed '$branch' → main, pushed to origin, worktree + branch removed. main ≡ origin/main."
