# AIfred project page

Static GitHub Pages site; no build dependencies are required.

## Run locally

From the repository root:

```powershell
python -m http.server 8000 --directory docs
```

Open <http://localhost:8000>. Check that the video loads, both task sliders move, and the setup figures fit the viewport.

## Publish

Push to `main`, then set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**. The `Deploy project page` workflow publishes `docs/` on each push. GitHub shows the URL under **Settings → Pages**.

The Paper and arXiv buttons currently point to `#`. Replace their `href` values in `index.html` when those links are available.
