# Registry configuration

Optional file **`workspace-registry.json`** at the root of the **forge-lenses** repository (next to `README.md`) is merged with built-in defaults by `load_registry()` in `lenses/registry.py`.

## Default values

If the file is missing or invalid JSON, defaults apply:

```json
{
  "external_urls": {
    "handbook": "https://blueprints.forgesdlc.com/",
    "forge": "https://forgesdlc.com/"
  },
  "ignore_paths": [],
  "website_labels": {}
}
```

## Keys

| Key | Type | Effect |
|-----|------|--------|
| `external_urls` | object | Shallow-merged into defaults. Keys `handbook` and `forge` set the Handbook and Forge links in the dashboard nav. |
| `ignore_paths` | array of strings | Top-level workspace directory **names** to omit from `children` (and thus from most dashboard sections). |
| `website_labels` | object | Map child directory name → short label string for the `/websites` page. |

## Example

See **`workspace-registry.example.json`** in the forge-lenses repo for a sample with `ignore_paths` and `website_labels`.

## Scanning note

`ignore_paths` is applied in **`scan_workspace`** against immediate child directory names. A helper `should_ignore_child` exists in `registry.py` for reuse but v1 scanning inlines the same check.
