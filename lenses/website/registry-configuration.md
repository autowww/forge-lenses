# Registry configuration

Optional file **`workspace-registry.json`** at the root of the **forge-lenses** repository (next to `README.md`) is merged with built-in defaults by `load_registry()` in `lenses/registry.py`.

If **`lenses-workspace-registry.json`** exists at the **workspace root** (the directory passed as `--workspace-root` or implied by `LENSES_WORKSPACE_ROOT`), it is merged **after** the forge-lenses file so per-machine or per-workspace overrides stay out of the submodule.

## Default values

If the file is missing or invalid JSON, defaults apply:

```json
{
  "external_urls": {
    "handbook": "https://blueprints.forgesdlc.com/",
    "forge": "https://forgesdlc.com/"
  },
  "ignore_paths": [],
  "website_labels": {},
  "project_urls": {},
  "project_summaries": {},
  "overview_metrics_manual": {}
}
```

## Keys

| Key | Type | Effect |
|-----|------|--------|
| `external_urls` | object | Shallow-merged into defaults. Keys `handbook` and `forge` set the Handbook and Forge links in the dashboard nav. |
| `ignore_paths` | array of strings | Top-level workspace directory **names** to omit from `children` (and thus from most dashboard sections). |
| `website_labels` | object | Map child directory name → short label string for the `/websites` page. |
| `project_urls` | object | Map child directory name → **https** URL for a public site or landing page. Shown on the **Projects** portal and the project dashboard as **Project site**. |
| `project_summaries` | object | Map child directory name → plain-text **long blurb** for the **Overview** repository cards. Overrides the README-derived excerpt when set for that name. |
| `overview_metrics_manual` | object | Optional **Overview** “time comparison” numbers (not measured by lenses). Suggested keys: **`human_hours_week`**, **`estimated_hours_without_genai`** (or alias **`hours_without_genai`**), **`estimated_hours_genai_potential`** (or **`hours_genai_potential`**), **`methodology_note`** (string). Merged into **`lenses-docs/overview-metrics.json`** when **`collect-lenses-overview-data.py`** runs. |
| `github_login` | string | Expected GitHub username for **POST `/api/auth/github`** and **POST `/api/actions/run`**. If empty, the server also tries **one** subdirectory name under **`<workspace>/.lenses-repo/`** or `gh api user` from the workspace. |
| `actions` | object | Allowlisted subprocess actions: map **site directory name** → map **action key** → `{ "argv": ["cmd", "…"], "cwd_relative": "child_dir" }`. **`cwd_relative`** must stay under the workspace root. No shell is used; **`argv`** is passed directly to `subprocess`. |

### `actions` example

```json
"actions": {
  "forgesdlc": {
    "build": {
      "argv": ["python3", "generator/build-site.py"],
      "cwd_relative": "forgesdlc"
    }
  },
  "blueprints-website": {
    "build": {
      "argv": ["python3", "generator/build-handbook.py", "--all"],
      "cwd_relative": "blueprints-website"
    },
    "inject_nav": {
      "argv": ["python3", "generator/inject-portal-nav.py"],
      "cwd_relative": "blueprints-website"
    }
  }
}
```

## Example

See **`workspace-registry.example.json`** in the forge-lenses repo for a sample with `ignore_paths`, `website_labels`, and `project_urls`.

## Scanning note

`ignore_paths` is applied in **`scan_workspace`** against immediate child directory names. A helper `should_ignore_child` exists in `registry.py` for reuse but v1 scanning inlines the same check.
