# Releasing documentation (static handbook)

Checklist for publishing **lenses.forgesdlc.com** (Firebase project **lenses-d0fdb**) from [`forge-lenses-website`](forge-lenses-website-handbook.md).

1. In **forge-lenses**: run **`bash scripts/check-docs.sh`** on a clean tree; fix nav/diagram/API coverage failures. Confirm **`lenses-docs/public-manifest.json`** exists post-build (**offline parity**), and skim **`python3 scripts/score-docs-readiness.py`** (JSON + Markdown under `build/`) if you expect a stakeholder sign-off.
2. Commit/push **forge-lenses** (including `docs/` + `kitchensink` submodule pointer if `forge-autodoc` changed upstream).
3. In **forge-lenses-website**: bump the `forge-lenses` submodule to that commit.
4. Run **`python3 generator/build-site.py`** (sets `build_profile=public` by default for that repo).
5. Smoke-test generated `website/` locally if desired; deploy Hosting (`firebase deploy --only hosting` or your CI).
   - Confirm emitted HTML basenames against bookmarks before authoring [`docs/redirects.yaml`](../redirects.yaml) (forge-autodoc uses short slugs like `05-studio-101.html`).
6. Optional: add matching **Firebase Hosting** `redirects` entries (see Firebase docs) when renaming public slugs — keep [`docs/redirects.yaml`](../redirects.yaml) as the authoring source of truth for static meta-refresh stubs.
7. Cross-site mirrors (Blueprints handbook / forgesdlc.com) use separate submodule bumps after editing the standalone **blueprints** repo.
