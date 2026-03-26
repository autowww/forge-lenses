# forge-lenses — reference handbook

This page is the **`/docs/`** home: **reference** pages for the **lenses** package (kitchensink `showcase_page`), built by `generator/build-lenses-docs.py` into **`lenses-docs/`**.

**Tutorial** (setup, submodules, publishing, extensions roadmap) lives in **`lenses/fa-tutorial-md/`**, built with **forge-autodoc** into **`lenses/tutorials/`** and synced to repo-root **`tutorial/`** for the dashboard **Tutorial** link:

```bash
pip install markdown PyYAML
./build-fa-tutorials.sh
```

Open **`/local-site/<repo>/tutorial/index.html`** on the lenses server (same host as the dashboard) after building.

## Reference (Python package)

Generated from **`lenses/website/`**:

- [Package architecture](architecture.html)
- [HTTP API and routes](http-api-and-routes.html)
- [Workspace scan contract](workspace-scan-contract.html)
- [Registry configuration](registry-configuration.html)
- [Dashboard pages](dashboard-pages.html)

**Optional — reference page preview images** on this home: install [html2image](https://pypi.org/project/html2image/) and Chromium or Google Chrome, then `python3 generator/build-lenses-docs.py --previews` or set **`LENSES_BUILD_DOC_PREVIEWS=1`**. PNGs are written under **`lenses-docs/previews/`**.
