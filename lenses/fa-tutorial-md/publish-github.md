# Publish forge-lenses on GitHub

The remote **`https://github.com/autowww/forge-lenses.git`** must exist before consumers can clone the submodule over HTTPS.

Create and push (authenticated as `autowww`):

```bash
cd /path/to/forge-lenses
gh repo create autowww/forge-lenses --public --source=. --remote=origin --push --description "Local workspace visualization for Blueprints / ForgeSDLC"
```

If the repo already exists but push failed:

```bash
git remote add origin https://github.com/autowww/forge-lenses.git
git push -u origin main
```

After the remote exists, submodule clones in other repos will resolve `forge-lenses` from GitHub.
