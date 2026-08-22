#!/usr/bin/env bash
# Playwright human-copy oracle gate for Forge Lenses Studio.
# Usage: ./scripts/studio-human-copy-oracle.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LE="${REPO_ROOT}/lenses-enterprise"

cd "${LE}"
npm run test:e2e:human-copy
echo "studio-human-copy-oracle: GREEN"
