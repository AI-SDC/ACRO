#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: scripts/generate_changelog.sh <version>"
    echo "Example: scripts/generate_changelog.sh 0.4.13"
    exit 1
fi

VERSION="$1"

if ! [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Version must be in SemVer format: X.Y.Z"
    exit 1
fi

if ! command -v git-cliff >/dev/null 2>&1; then
    echo "git-cliff is not installed."
    echo "Install instructions: https://git-cliff.org/docs/installation"
    exit 1
fi

git cliff --config cliff.toml --unreleased --tag "v${VERSION}" --prepend CHANGELOG.md

echo "CHANGELOG.md updated for v${VERSION}."
echo "Review and edit CHANGELOG.md before committing."
