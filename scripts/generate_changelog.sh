#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
    echo "Usage: scripts/generate_changelog.sh"
    exit 1
fi

if ! command -v git-cliff >/dev/null 2>&1; then
    echo "git-cliff is not installed."
    echo "Install instructions: https://git-cliff.org/docs/installation"
    exit 1
fi

if [[ ! -f CHANGELOG.md ]]; then
    echo "CHANGELOG.md not found in current directory."
    exit 1
fi

TEMP_CHANGELOG="$(mktemp)"
trap 'rm -f "${TEMP_CHANGELOG}"' EXIT

git cliff --config cliff.toml --unreleased --output "${TEMP_CHANGELOG}"

PYTHON_OUTPUT="$(
    python3 - "${TEMP_CHANGELOG}" "CHANGELOG.md" <<'PY'
import sys
from pathlib import Path

generated_path = Path(sys.argv[1])
changelog_path = Path(sys.argv[2])

generated_lines = generated_path.read_text(encoding="utf-8").splitlines()
changelog_lines = changelog_path.read_text(encoding="utf-8").splitlines()

generated_bullets: list[str] = []
seen_generated: set[str] = set()
for line in generated_lines:
    if line.startswith("*   ") and line not in seen_generated:
        generated_bullets.append(line)
        seen_generated.add(line)

if not generated_bullets:
    print("ADDED_COUNT=0")
    sys.exit(0)

insert_idx = None
for idx, line in enumerate(changelog_lines):
    if line.startswith("## Version "):
        insert_idx = idx
        break

if insert_idx is None:
    print("ERROR: No '## Version ...' heading found in CHANGELOG.md")
    sys.exit(2)

existing_lines = set(changelog_lines)
new_bullets = [line for line in generated_bullets if line not in existing_lines]

if not new_bullets:
    print("ADDED_COUNT=0")
    sys.exit(0)

updated_lines = (
    changelog_lines[: insert_idx + 1]
    + new_bullets
    + changelog_lines[insert_idx + 1 :]
)
changelog_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

print(f"ADDED_COUNT={len(new_bullets)}")
for line in new_bullets:
    print(f"ADDED_LINE={line}")
PY
)"

ADDED_COUNT="$(printf '%s\n' "${PYTHON_OUTPUT}" | awk -F= '/^ADDED_COUNT=/{print $2}')"

if [[ -z "${ADDED_COUNT}" ]]; then
    echo "Could not determine how many changelog entries were added."
    exit 1
fi

if [[ "${ADDED_COUNT}" == "0" ]]; then
    echo "No new changelog entries to add under the current top version."
    exit 0
fi

echo "CHANGELOG.md updated."
echo "Inserted ${ADDED_COUNT} new entry/entries under the current top version section."
printf '%s\n' "${PYTHON_OUTPUT}" | awk -F= '/^ADDED_LINE=/{print "  - " $2}'
echo "Review and edit CHANGELOG.md before committing."
