#!/bin/sh
# Releases pin released infra (D5, docs/versioning.md): the infra/ gitlink must
# point at a commit carrying an infra v* tag. Exit 0 tagged / 1 untagged / 2 error.
# Works initialized (offline, asks the submodule) or uninitialized (CI: ls-remote).
set -eu

sha=$(git ls-tree HEAD infra | awk '{print $3}')
[ -n "$sha" ] || { echo "check_release_pins: FATAL no infra gitlink in HEAD" >&2; exit 2; }

if [ -e infra/.git ]; then
  tags=$( (cd infra && git tag --points-at "$sha") | grep '^v' || true)
else
  url=$(git config -f .gitmodules submodule.infra.url)
  [ -n "$url" ] || { echo "check_release_pins: FATAL no submodule.infra.url" >&2; exit 2; }
  # ls-remote lists both refs/tags/vX and peeled refs/tags/vX^{}; match either at our sha.
  tags=$(git ls-remote --tags "$url" \
    | awk -v s="$sha" '$1==s {print $2}' \
    | sed -e 's|^refs/tags/||' -e 's|\^{}$||' | grep '^v' | sort -u || true)
fi

if [ -n "$tags" ]; then
  printf 'check_release_pins: OK — infra %s carries tag(s): %s\n' "$sha" "$tags"
  exit 0
fi
printf 'check_release_pins: REFUSE — infra gitlink %s carries no v* tag.\n' "$sha" >&2
printf 'Tag infra first (babylon-infra: mise run release:bump), bump the gitlink, retry.\n' >&2
exit 1
