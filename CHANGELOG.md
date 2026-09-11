# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

### Removed
- **Breaking:** Netlify `_redirects` generation, along with the `redirect_mechanism` config option. Redirects are now always HTML meta-refresh pages. Remove `redirect_mechanism` from `mkdocs.yml` — MkDocs reports a leftover value as an unrecognised option and ignores it, and fails the build under `--strict`.

### Fixed
- Front matter is no longer missed on files saved with a UTF-8 byte-order mark. MkDocs reads sources as `utf-8-sig`, so such pages built normally while their `id` was silently dropped and every link to it failed to resolve.
- Front matter closed with `...` instead of `---` is now recognised. MkDocs accepts both terminators.
- Pages generated in memory by other plugins (MkDocs 1.6 `File.generated`) are now indexed. Previously they were skipped because they have no path on disk.
- Generated redirect pages and the ID index page are written with LF line endings on every platform, so a site built on Windows is byte-identical to one built on Linux.
- Protected path collisions are detected against build output rather than `docs_dir` contents. A page at `docs/go.md` builds to `go/index.html` and was silently overwritten by the generated index page, because the old check only looked for a `go` *directory* in the source tree. Warnings now name the source file and its output path, and distinguish content that is overwritten from content that merely sits inside `redirect_path`.
- `id:` links inside four-space indented code blocks are no longer rewritten. Only fenced and inline code were protected, so a page documenting the `id:` syntax in an indented block had its example silently turned into a real link. Indented list continuations, which share the same indentation, still resolve normally.
- Reference-style link definitions (`[ref]: id:page-id`) are now resolved. They previously passed through untouched and reached the output as a broken `href="id:page-id"`, with no warning even under `on_unresolved: error`.
- `__version__` is read from installed package metadata instead of being hardcoded. It had drifted to `0.1.0` while the package was at `0.1.2`.

### Changed
- **Breaking:** the minimum supported MkDocs version is now 1.6 (was 1.5). Page sources are read through `File.content_string`, a 1.6 API, and the fallback that kept 1.5 working has been removed. Indexing pages generated in memory by other plugins also requires 1.6.
- Unresolved IDs are listed once each in the `on_unresolved: error` message rather than repeated per occurrence.
- Front matter is parsed with MkDocs' own reader (`mkdocs.utils.meta.get_data`) and sourced via `File.content_string`, so the index sees exactly the metadata MkDocs puts on `page.meta`.
- Removed the 8 KB front-matter read cap added in 0.1.2. It bounded nothing in practice — MkDocs reads each documentation page in full moments later regardless — while causing IDs to be dropped silently on pages with large front matter.

## [0.1.2] - 2026-06-10

### Fixed
- Redirect targets and index page URLs now include the sub-path from `site_url`, fixing redirects on sites hosted under a sub-path (e.g. GitHub Pages project sites).

### Security
- `redirect_path` config is validated against a strict character allowlist and checked to resolve inside the site directory.
- Front-matter scanning is capped at 8 KB per file, with a warning when the closing delimiter falls outside the window.
- GitHub Actions are SHA-pinned in all workflows, workflow permissions are restricted to `contents: read`, and Dependabot keeps action pins current.

### Changed
- Code-block placeholder restoration in the link resolver is now a single pass that tolerates stray sentinel sequences in source markdown.
- Added ruff linting (with a CI lint job) and default pytest coverage reporting.

## [0.1.1] - 2026-04-03

### Changed
- Removed `mkdocs-material` as a hard dependency. The plugin works with any MkDocs theme and already fell back to bare HTML when the theme template was unavailable.

## [0.1.0] - 2026-04-02

Initial release.

### Features
- `id:` link syntax — write `[text](id:page-id)` in any markdown file; the plugin resolves it to the correct relative path at build time.
- Front-matter ID registration — assign a stable ID to any page via `id: my-page-id` in its YAML front matter.
- Duplicate and invalid ID detection — duplicate IDs raise a build error; invalid formats (anything other than lowercase letters, numbers, and hyphens) emit a warning.
- HTML redirect pages — generates `<redirect_path>/<id>/index.html` with a meta-refresh for each registered ID.
- Stable link index page — generates a themed (or bare-HTML fallback) index page at `/<redirect_path>/` listing all registered IDs, titles, and URLs.
- `mkdocs serve` compatibility — the ID index is rebuilt on every file change so links stay current during live preview.
- `mkdocs-macros-plugin` ordering check — warns if `macros` is listed after `stablelinks` in `mkdocs.yml`, which can cause snippet `include` tags to resolve incorrectly.
- Code block protection — `id:` syntax inside fenced and inline code blocks is left untouched.
- Configurable `on_unresolved` behaviour — either `warn` (default) or `error`.
