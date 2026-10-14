# mkdocs-stablelinks-plugin

[![PyPI](https://img.shields.io/pypi/v/mkdocs-stablelinks-plugin)](https://pypi.org/project/mkdocs-stablelinks-plugin/)

Stable internal linking and durable external URLs for [MkDocs](https://www.mkdocs.org/) via a page ID system.

Authors declare a stable `id` in page front matter. Internal links use `id:` syntax resolved at build time. External durable links use `/go/<id>/` redirect pages that update automatically when pages move.

## Installation

```
pip install mkdocs-stablelinks-plugin
```

**Requires Python 3.10+.**

## Quick start

Add the plugin to `mkdocs.yml`:

```yaml
plugins:
  - search
  - stablelinks
```

Declare an ID in any page's front matter:

```yaml
---
id: install-windows
---
```

Link to that page from anywhere in the site using the `id:` syntax:

```markdown
[Install on Windows](id:install-windows)
[Install on Windows](id:install-windows#prerequisites)
```

Reference-style links work too — put the `id:` in the definition:

```markdown
See the [installation guide][install].

[install]: id:install-windows
```

At build time, `id:` links are rewritten to standard relative URLs. If the page moves, only its front matter path changes — all links continue to work.

`id:` links inside code are left alone, so you can write about the syntax without it being rewritten. This covers fenced blocks, inline code, and four-space indented blocks.

## Configuration

```yaml
plugins:
  - stablelinks:
      redirect_path: go           # URL prefix for redirect pages (default: go)
      index_page: true            # generate /go/ index listing (default: true)
      on_unresolved: warn         # warn | error (default: warn)
```

All options are optional. The minimal installation works with no configuration at all.

| Option | Default | Accepted values | Description |
|--------|---------|-----------------|-------------|
| `redirect_path` | `go` | Any valid URL segment | URL prefix used for all redirect pages and the index page. A page with `id: install-windows` produces a redirect at `/<redirect_path>/install-windows/`. Changing this value after publishing will break any external links that used the old path. |
| `index_page` | `true` | `true`, `false` | When enabled, generates a page at `/<redirect_path>/` listing all registered IDs, their titles, and current URLs. The page inherits the site theme and is excluded from search results. Shares the same path as `redirect_path`. |
| `on_unresolved` | `warn` | `warn`, `error` | What to do when an `id:` link references an ID that no page declares. `warn` logs a warning and preserves the original `id:` syntax in the output. `error` fails the build. |

## ID format

```yaml
---
id: install-windows
---
```

IDs must:
- Contain only lowercase letters, numbers, and hyphens
- Be unique across the entire site

Pages without an `id` are unaffected by the plugin.

## Link syntax

```markdown
[link text](id:page-id)
[link text](id:page-id#anchor)
```

Anchor fragments are passed through as-is. The plugin does not validate that an anchor exists on the target page.

## Redirect pages

For each page with an `id`, an HTML meta-refresh page is written to `<site>/<redirect_path>/<id>/index.html`:

```html
<meta http-equiv="refresh" content="0; url=/install/windows/">
<link rel="canonical" href="/install/windows/">
```

Share `/go/install-windows/` as a durable external link. When the page moves, regenerate the site — the redirect updates automatically.

## ID index page

When `index_page: true`, a page listing all registered IDs is generated at `/<redirect_path>/`. It shows each ID, its title, and its current URL.

## mkdocs-macros-plugin compatibility

If you use [mkdocs-macros-plugin](https://mkdocs-macros-plugin.readthedocs.io/) with snippets, list it **before** stablelinks:

```yaml
plugins:
  - search
  - macros
  - stablelinks
```

If macros is listed after stablelinks, the plugin emits a warning at build time.

## Error conditions

| Condition | Severity |
|-----------|----------|
| Duplicate `id` across pages | Error (always) |
| Unresolved `id:` link | Configurable (`warn` or `error`) |
| Invalid `id` format | Warning |
| Site content builds into `redirect_path` | Warning (names the file, and says whether a generated page overwrites it) |
| macros listed after stablelinks | Warning |

Unresolved `id:` links are preserved in output rather than generating broken HTML.

## Limitations

- Anchor fragments in `id:` links are not validated against the target page's headings.
- The ID index page renders using the site theme when possible and falls back to bare HTML for unsupported themes.
- Redirects are HTML meta-refresh pages only. Server-side redirect formats are not generated.
