#!/usr/bin/env bash
# Spec 061 US7 (T104, FR-029): CI gate — fail if any Python module
# re-introduces the mock-bridge scaffolding deleted by FR-032.
#
# A line is considered a re-introduction when it references one of the
# deleted symbols AS A LIVE CODE REFERENCE — i.e., not as documentation
# that the symbol was removed. The filter excludes:
#   - __pycache__ artifacts
#   - migrations/ (commit-frozen text documenting the cutover)
#   - tests/scripts/ (this script itself)
#   - lines containing 'removed' / 'deleted' / 'deprecated' / 'no longer'
#     / 'legacy' / 'spec 061' / 'FR-032' (post-hoc deprecation comments)

set -euo pipefail
SEARCH='MockEngineBridge|mock_defines|seed_mock_game|BABYLON_MOCK_MODE'

matches=$(grep -rnE "${SEARCH}" src/ web/ \
    --include="*.py" \
    --exclude-dir=__pycache__ \
    --exclude-dir=migrations \
    --exclude-dir=scripts \
    | grep -vE '(removed|deleted|deprecated|no longer|legacy|spec 061|Spec 061|FR-032)' \
    || true)

if [ -n "${matches}" ]; then
    echo "[FAIL] spec 061 US7 — mock-bridge scaffolding leaked back in:" >&2
    echo "${matches}" >&2
    exit 1
fi
echo "[OK] spec 061 US7 — no mock-bridge scaffolding in Python sources."
