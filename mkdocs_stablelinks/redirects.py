"""Redirect page generation — HTML meta refresh and Netlify _redirects."""

import html as html_lib
import logging
import os
from typing import List

from .index import IDIndex

log = logging.getLogger("mkdocs.plugins.stablelinks")

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={url}">
  <link rel="canonical" href="{url}">
  <title>Redirecting...</title>
</head>
<body>
  <p>Redirecting to <a href="{url}">{url}</a></p>
</body>
</html>
"""

_NETLIFY_HEADER = (
    "# mkdocs-stablelinks \u2014 auto-generated, do not edit below this line\n"
)


def generate_html_redirects(
    index: IDIndex,
    redirect_path: str,
    site_dir: str,
) -> None:
    """Write an HTML meta-refresh page for each registered page ID."""
    for entry in index.all_entries():
        if entry.url is None:
            log.warning(
                "mkdocs-stablelinks: Skipping HTML redirect for id '%s' — "
                "page URL not available.",
                entry.page_id,
            )
            continue

        # Ensure the URL starts with /
        page_url = entry.url if entry.url.startswith("/") else f"/{entry.url}"

        out_dir = os.path.join(site_dir, redirect_path, entry.page_id)
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "index.html")

        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(_HTML_TEMPLATE.format(url=html_lib.escape(page_url)))


def generate_netlify_redirects(
    index: IDIndex,
    redirect_path: str,
    site_dir: str,
) -> None:
    """Write stablelinks redirect rules to _redirects at the site root.

    If _redirects already exists, any previously written stablelinks block
    (identified by _NETLIFY_HEADER) is replaced so repeated builds don't
    accumulate duplicate rules.
    """
    redirects_file = os.path.join(site_dir, "_redirects")

    lines: List[str] = [_NETLIFY_HEADER]
    for entry in index.all_entries():
        if entry.url is None:
            continue
        page_url = entry.url if entry.url.startswith("/") else f"/{entry.url}"
        lines.append(f"/{redirect_path}/{entry.page_id}/ {page_url} 301\n")

    if len(lines) == 1:
        # Nothing to write beyond the header
        return

    # Preserve any user-managed content that precedes the stablelinks block.
    existing = ""
    if os.path.exists(redirects_file):
        with open(redirects_file, "r", encoding="utf-8") as fh:
            content = fh.read()
        marker = content.find(_NETLIFY_HEADER)
        existing = content[:marker] if marker != -1 else content

    with open(redirects_file, "w", encoding="utf-8") as fh:
        if existing:
            fh.write(existing)
        fh.writelines(lines)
