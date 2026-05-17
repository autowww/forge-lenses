---


nav_title: Studio troubleshooting
public_publish: true
audience: public
product_area: studio
tier: practitioner
handbook_area: studio
learning_level: '201'
section: studio-wizard
description: Blank Studio shell, assets, and wrong API origin — Studio-focused quick fixes.
status: shipped
page_type: topic
---

# Studio — troubleshooting

## What it is

Fast checks for **Forge Studio** (`/studio/`) when the shell is blank, assets 404, or XHR hits the **wrong host**. Product-wide recovery lives in [Troubleshooting](12-troubleshooting.md); this page stays **Studio-specific**.

## When to use it

Symptoms during [Studio 101](05-studio-101.md) or daily review — before assuming a regression in backend logic.

## Blank Studio / white screen

1. Confirm `http://127.0.0.1:8080/studio/` returns **200** (adjust **host/port**).
2. Open devtools → **Console** for failed **chunk** loads (stale `lenses-enterprise` build).
3. Ensure API calls target the **same origin** as the HTML — mismatched `LENSES_PUBLIC_ORIGIN` causes CORS-like symptoms.

## Asset load failures

1. Look for **404** on `/studio/assets/*` — rebuild `lenses-enterprise` (`npm run build`) if hash mismatch.
2. Hard-refresh after upgrading Lenses; service-worker caching is off by default but enterprise proxies may cache.

## Wrong API origin

1. Filter Network tab for **`/api/`** — paths should hit your Lenses host, not an old Forge Fleet URL.
2. Cross-check [Configuration reference](../reference/config-env.md) for `LENSES_*` overrides that rewrite Studio’s fetch base.

## Decision aid

See the **blank Studio** diagram in [Studio route atlas](14-studio-route-map.md) for the same decision tree in visual form.

## Verify

After fixes, `/studio/` shows **chrome + sidebar** and **`/api/auth/status`** (or your first Studio XHR) returns from the **expected host**.

## What to do next

- [Troubleshooting](12-troubleshooting.md)
- [Install and run](02-install-and-run.md)
