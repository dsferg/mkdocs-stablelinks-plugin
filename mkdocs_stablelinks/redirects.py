"""Redirect page generation — HTML meta refresh pages."""

import html as html_lib
import logging
import os

from .index import IDIndex
from .utils import absolute_url

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


def generate_html_redirects(
    index: IDIndex,
    redirect_path: str,
    site_dir: str,
    url_prefix: str = "",
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

        page_url = absolute_url(url_prefix, entry.url)

        out_dir = os.path.join(site_dir, redirect_path, entry.page_id)
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "index.html")

        # newline="" writes the template's \n unchanged, so output is
        # byte-identical whichever platform the site is built on.
        with open(out_file, "w", encoding="utf-8", newline="") as fh:
            fh.write(_HTML_TEMPLATE.format(url=html_lib.escape(page_url)))
