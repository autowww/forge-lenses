#!/usr/bin/env sh
# Copy React primitives from forgesdlc-kitchensink into this package for Vite/tsc (single source of truth in KS).
set -e
cd "$(dirname "$0")/.."
KS="../../forgesdlc-kitchensink/react"
DST="src/forgesdlc-kitchensink"
for f in \
  WorkspaceLensControl.tsx \
  workspaceLensTypes.ts \
  TileDropdownControl.tsx \
  tileDropdownTypes.ts \
  index.ts \
  forgeRunTypes.ts \
  ForgeKeyValueGrid.tsx \
  ForgeStatusBanner.tsx \
  ForgeRunHeader.tsx \
  ForgeWorkflowStageBar.tsx \
  ForgeDecisionActionBar.tsx \
  ForgeEventTimeline.tsx \
  ForgeDiagnosticPanel.tsx \
  ForgeReviewPanel.tsx
do
  cp "$KS/$f" "$DST/"
done
echo "Synced $KS -> $DST"
