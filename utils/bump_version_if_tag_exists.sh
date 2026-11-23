#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=utils/exit_codes.sh
source "$(dirname "$0")/exit_codes.sh"

version="$1"

# Whether <branch> on the remote is now a newer commit built on the one this
# run started from (HEAD~1, under the bump commit). Two merges close together
# do that, and the later one's run will release both. A rewritten branch, or a
# push refused for any other reason, is a real failure.
branch_moved_on() {
  local started_from
  started_from="$(git rev-parse HEAD~1)" || return 1
  git fetch --quiet origin "$1" || return 1
  [[ "$(git rev-parse FETCH_HEAD)" != "${started_from}" ]] &&
    git merge-base --is-ancestor "${started_from}" FETCH_HEAD
}

if git rev-parse -q --verify "refs/tags/v${version}" >/dev/null; then
  branch_name="$(git symbolic-ref --quiet --short HEAD || true)"
  branch_name="${branch_name:-${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-}}}"

  if [[ -z "${branch_name}" ]]; then
    echo "Unable to determine branch name for release version bump" >&2
    exit "${EXIT_FAILURE}"
  fi

  git config user.name "github-actions[bot]"
  git config user.email "github-actions[bot]@users.noreply.github.com"
  git mkver patch >/dev/null
  version=$(python utils/read_version.py)
  uv lock
  git add VERSION uv.lock
  git commit -m "chore: bump version to ${version}" >/dev/null
  if ! git push origin "HEAD:${branch_name}"; then
    if branch_moved_on "${branch_name}"; then
      echo "${branch_name} gained a newer commit while this run was releasing;" \
        "the run for that commit releases this one's changes too" >&2
      exit "${EXIT_SUPERSEDED}"
    fi
    echo "git push failed; version bump commit not pushed" >&2
    exit "${EXIT_FAILURE}"
  fi
fi

printf '%s\n' "$version"
