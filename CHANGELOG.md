# Changelog

All notable changes to this project will be documented here.

## [0.1.1] - 2026-04-03

### Fixed
- `generate_netlify_redirects` now overwrites its own block in `_redirects` rather than appending, preventing duplicate rules on repeated builds or during `mkdocs serve`.

### Changed
- Removed `mkdocs-material` as a hard dependency. The plugin works with any MkDocs theme and already fell back to bare HTML when the theme template was unavailable.

## [0.1.0] - 2026-04-02

Initial release.

### Features
- `id:` link syntax — write `[text](id:page-id)` in any markdown file; the plugin resolves it to the correct relative path at build time.
- Front-matter ID registration — assign a stable ID to any page via `id: my-page-id` in its YAML front matter.
- Duplicate and invalid ID detection — duplicate IDs raise a build error; invalid formats (anything other than lowercase letters, numbers, and hyphens) emit a warning.
- HTML redirect pages — generates `<redirect_path>/<id>/index.html` with a meta-refresh for each registered ID (configurable, on by default).
- Netlify redirect rules — appends `/<redirect_path>/<id>/ <url> 301` entries to `_redirects` (configurable, on by default).
- Stable link index page — generates a themed (or bare-HTML fallback) index page at `/<redirect_path>/` listing all registered IDs, titles, and URLs.
- `mkdocs serve` compatibility — the ID index is rebuilt on every file change so links stay current during live preview.
- `mkdocs-macros-plugin` ordering check — warns if `macros` is listed after `stablelinks` in `mkdocs.yml`, which can cause snippet `include` tags to resolve incorrectly.
- Code block protection — `id:` syntax inside fenced and inline code blocks is left untouched.
- Configurable `on_unresolved` behaviour — either `warn` (default) or `error`.
