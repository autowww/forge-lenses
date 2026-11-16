---

nav_title: Scenario — Live deploy parity
public_publish: true
audience: public
product_area: lenses
learning_level: reference
section: builders
description: Post-deploy handshake between public manifest metadata and Hosting HTML.
status: shipped
tier: builder
handbook_area: builders
page_type: topic
---

# Scenario — Live deploy parity drill

## Scenario summary

After Firebase Hosting publishes `forge-lenses-website`, compare production HTML `<meta>` tags with `lenses-docs/public-manifest.json` from CI.

## User role

Release engineer.

## Starting state

- Local `bash scripts/check-docs.sh` succeeded on release SHA.
- `python3 scripts/check-live-docs-parity.py` available with outbound network approved.

## Steps

1. Export manifest JSON artifact from CI or rerun `generator/build-lenses-docs.py`.
2. Run `python3 scripts/check-live-docs-parity.py --allow-network`.
3. Note mismatches in maintainer release notes if CDN caching delays meta refresh.

## Example input

```bash
python3 scripts/check-live-docs-parity.py --allow-network
```

## Example output or expected state

Script reports nav hash alignment or prints explicit diff fields for follow-up.

## Verification

- Manifest `nav_sha256` matches meta tag on `https://lenses.forgesdlc.com/index.html` after hard refresh.
- `build/docs-readiness.json` archived for the same SHA.

## Failure / recovery

Invalidate Hosting cache, confirm submodule pointer, redeploy `forge-lenses-website`, rerun parity script.

## Related API/schema docs

[Docs versioning](25-docs-versioning.md) + [Release notes](24-release-notes.md).
