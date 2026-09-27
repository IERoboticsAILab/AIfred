# AIfred project page

Static GitHub Pages site; no build dependencies are required.

## Run locally

From the repository root:

```powershell
python -m http.server 8000 --directory docs
```

Open <http://localhost:8000>. Check that the video loads, both task sliders move, and the setup figures fit the viewport.

## Publish

Before the first deployment, a repository admin must enable Pages: open **Settings → Pages**, then set **Build and deployment → Source** to **GitHub Actions**. The workflow cannot create the Pages site using GitHub's built-in workflow token; without this one-time setting, `configure-pages` returns `Not Found`.

Then push to `main` or rerun **Actions → Deploy project page**. The workflow publishes `docs/` and GitHub shows the URL under **Settings → Pages**.

The arXiv button currently points to `#`. Replace its `href` in `index.html` when the preprint is available.
