# Publishing forge-lenses docs to blueprints.forgesdlc.com

User-facing documentation that appears under **`https://blueprints.forgesdlc.com/lenses/`** is built from **only** the explicit allowlist in **blueprints-website** [`generator/handbook-publish-manifest.yaml`](https://github.com/autowww/blueprints-website/blob/main/generator/handbook-publish-manifest.yaml) (`forge_lenses` section). Sources live in this repository under:

- `docs/handbook-public/*.md`

…staged by **blueprints-website** (`generator/tooling_handbooks.py`) into **`/lenses/guides/`** on the public site. The full `docs/` tree (ADRs, Studio shell notes, Wizard internals, etc.) is **not** mirrored to the public site; it remains for maintainers and local **`lenses-docs/`** builds (`generator/build-lenses-docs.py`). Legacy **`/lenses/handbook/*`** URLs on the hosting domain redirect to the hub or guides — do not treat that path as a second public doc tree.

## Rules

Follow **[Blueprints documentation design principles](https://github.com/autowww/blueprints/blob/main/docs/DESIGN-PRINCIPLES.md)** — in particular:

- **Stricter bar** for `product_area` **lenses**, **studio**, or **wizard**: purpose, prerequisites, getting started, 101/201/301 tutorials, recipes, troubleshooting, minimal operator settings only.
- **`public_publish`**: **`public_publish: true` is required** for a handbook-public file to stage to the site (allowlist match alone is not enough). **`public_publish: false`** excludes a page even if it matches an include glob.
- **Bulk allowlist**: paths in the manifest are **relative to `docs/handbook-public/`**.

## Metadata example

```yaml
---
audience: public
tier: 101
public_publish: true
nav_group: Wizard
product_area: wizard
nav_title: Get started with the Blueprints Wizard
---
```

After editing, bump the **forge-lenses** submodule in **blueprints-website** and rebuild.
