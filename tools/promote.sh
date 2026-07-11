#!/usr/bin/env bash
# Promotion gate (Program 15 Phase 8, owner ruling 3): dev -> main is a
# DIRECT FAST-FORWARD push, guarded by this script rather than a GitHub
# ruleset — GitHub cannot require status checks on direct pushes, so the
# script IS the gate. It verifies:
#   1. dev is a clean fast-forward ahead of main (never diverged);
#   2. every completed check run on dev HEAD is green (none red, none missing);
#   3. the operator confirms.
# Then: git push origin dev:main. Releases do NOT fire on promotion —
# release.yml is tag-driven (run `mise run bump` on dev first when a
# release is intended; the bump commit + tag ride this same ff).
set -euo pipefail

REMOTE="${REMOTE:-origin}"

echo "==> Fetching ${REMOTE}..."
git fetch "$REMOTE" dev main

DEV_SHA=$(git rev-parse "${REMOTE}/dev")
MAIN_SHA=$(git rev-parse "${REMOTE}/main")

echo "    ${REMOTE}/dev  = ${DEV_SHA}"
echo "    ${REMOTE}/main = ${MAIN_SHA}"

if [ "$DEV_SHA" = "$MAIN_SHA" ]; then
    echo "==> main already at dev HEAD — nothing to promote."
    exit 0
fi

# --- Gate 1: strict fast-forward ---------------------------------------------
if ! git merge-base --is-ancestor "$MAIN_SHA" "$DEV_SHA"; then
    echo "ERROR: ${REMOTE}/main is not an ancestor of ${REMOTE}/dev — the ff" >&2
    echo "       promotion model is broken (main diverged). Resolve manually." >&2
    exit 1
fi
AHEAD=$(git rev-list --count "${MAIN_SHA}..${DEV_SHA}")
echo "==> Fast-forward OK: dev is ${AHEAD} commit(s) ahead of main."

# --- Gate 2: dev HEAD check runs all green ------------------------------------
echo "==> Checking CI verdicts on dev HEAD..."
CHECKS_JSON=$(gh api "repos/{owner}/{repo}/commits/${DEV_SHA}/check-runs" --paginate)

# GitHub's own "Dependabot Updates" workflow (a `dynamic` event, NOT one of our
# CI jobs) attaches a check run named exactly "Dependabot" to whatever SHA is
# dev HEAD. It is a dependency *scan*, not a CI verdict: it can grind 30+
# minutes after a manifest-heavy push (lockfile/pyproject churn), and it recurs
# on GitHub's own schedule — so it may sit PENDING, or re-run, long after our
# real CI has gone green. Today it blocked a promotion for exactly that reason.
#
# Advisory jobs are the second class we must drop. main.yml's `continue-on-error`
# jobs (AI Tests, Image Scan) are DESIGNED not to gate — but GitHub still records
# their failing outcome as a `failure` check-run conclusion. When main.yml is
# dispatched on dev for a pre-promotion proving run, those check-runs land on dev
# HEAD, and a permanently-red advisory (e.g. Image Scan's postgis-bullseye CVEs,
# owner item 45) would wedge gate 2 forever. Our Loud Failure convention puts the
# word "advisory" in every such job name ("AI Tests (advisory — non-deterministic)",
# "Image Scan (trivy — advisory until postgis bump)"), so that word is a reliable,
# self-documenting filter — exactly parallel to the Dependabot case. No blocking
# job name contains it; every advisory one does.
CI_CHECKS=$(echo "$CHECKS_JSON" | jq '[.check_runs[]
  | select(.name != "Dependabot")
  | select(.name | ascii_downcase | contains("advisory") | not)]')

TOTAL=$(echo "$CI_CHECKS" | jq 'length')
if [ "$TOTAL" -eq 0 ]; then
    echo "ERROR: no check runs found on dev HEAD ${DEV_SHA} — push dev and let" >&2
    echo "       the fast lane finish before promoting." >&2
    exit 1
fi

PENDING=$(echo "$CI_CHECKS" | jq -r '.[] | select(.status != "completed") | .name')
if [ -n "$PENDING" ]; then
    echo "ERROR: checks still running on dev HEAD:" >&2
    while IFS= read -r line; do echo "       - $line" >&2; done <<< "$PENDING"
    exit 1
fi

# neutral/skipped are acceptable conclusions (gated jobs); failures are not.
BAD=$(echo "$CI_CHECKS" | jq -r '.[] | select(.conclusion as $c | ["success","neutral","skipped"] | index($c) | not) | "\(.name): \(.conclusion)"')
if [ -n "$BAD" ]; then
    echo "ERROR: non-green checks on dev HEAD:" >&2
    while IFS= read -r line; do echo "       - $line" >&2; done <<< "$BAD"
    exit 1
fi
echo "==> All ${TOTAL} completed checks green (success/neutral/skipped)."

# --- Gate 3: operator confirmation --------------------------------------------
echo ""
echo "About to promote: git push ${REMOTE} ${DEV_SHA}:refs/heads/main (${AHEAD} commits)"
read -r -p "Proceed? [y/N] " ANSWER
case "$ANSWER" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1 ;;
esac

git push "$REMOTE" "${DEV_SHA}:refs/heads/main"
echo "==> Promoted. main.yml (full pipeline) fires on this push."
