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

At build time, `id:` links are rewritten to standard relative URLs. If the page moves, only its front matter path changes — all links continue to work.

## Configuration

```yaml
plugins:
  - stablelinks:
      redirect_path: go           # URL prefix for redirect pages (default: go)
      redirect_mechanism: both    # html | netlify | both (default: both)
      index_page: true            # generate /go/ index listing (default: true)
      on_unresolved: warn         # warn | error (default: warn)
```

All options are optional. The minimal installation works with no configuration at all.

| Option | Default | Accepted values | Description |
|--------|---------|-----------------|-------------|
| `redirect_path` | `go` | Any valid URL segment | URL prefix used for all redirect pages and the index page. A page with `id: install-windows` produces a redirect at `/<redirect_path>/install-windows/`. Changing this value after publishing will break any external links that used the old path. |
| `redirect_mechanism` | `both` | `html`, `netlify`, `both` | Which redirect format(s) to generate. `html` writes a meta-refresh page for each ID under `<site>/<redirect_path>/`. `netlify` appends 301 rules to `_redirects` at the site root. `both` does both. Use `netlify` alone if you deploy to Netlify and want server-side redirects without the extra HTML files. |
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

For each page with an `id`, the plugin can generate one or both of the following redirect mechanisms (controlled by `redirect_mechanism`):

### HTML meta refresh

A file is written to `<site>/<redirect_path>/<id>/index.html`:

```html
<meta http-equiv="refresh" content="0; url=/install/windows/">
<link rel="canonical" href="/install/windows/">
```

Share `/go/install-windows/` as a durable external link. When the page moves, regenerate the site — the redirect updates automatically.

### Netlify `_redirects`

Rules are written to `_redirects` at the site root:

```
# mkdocs-stablelinks — auto-generated, do not edit below this line
/go/install-windows/ /install/windows/ 301
```

Existing `_redirects` content is preserved.

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
| `redirect_path` collides with docs content | Warning |
| macros listed after stablelinks | Warning |

Unresolved `id:` links are preserved in output rather than generating broken HTML.

## Limitations

- Anchor fragments in `id:` links are not validated against the target page's headings.
- The ID index page renders using the site theme when possible and falls back to bare HTML for unsupported themes.
- `redirect_mechanism: netlify` generates a plain `_redirects` file; no other server-side redirect formats are supported.
