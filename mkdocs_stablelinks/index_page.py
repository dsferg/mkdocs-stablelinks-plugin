"""ID index page generation."""

import logging
import os
from typing import List

from .index import IDIndex

log = logging.getLogger("mkdocs.plugins.stablelinks")


def generate_index_page(
    index: IDIndex,
    redirect_path: str,
    site_dir: str,
) -> None:
    """
    Write the ID index page to <site_dir>/<redirect_path>/index.html.

    The page is a standalone HTML file (not theme-integrated) listing all
    registered IDs with their titles and URLs.
    """
    rows = []
    for entry in index.all_entries():
        if entry.url is None:
            continue
        page_url = entry.url if entry.url.startswith("/") else f"/{entry.url}"
        title = entry.title or entry.page_id
        rows.append({"id": entry.page_id, "title": title, "url": page_url})

    if not rows:
        return

    out_dir = os.path.join(site_dir, redirect_path)
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "index.html")

    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write(_build_html(rows))


def _build_html(rows: List[dict]) -> str:
    table_rows = "\n      ".join(
        f"<tr>"
        f"<td><code>{r['id']}</code></td>"
        f"<td><a href=\"{r['url']}\">{r['title']}</a></td>"
        f"<td><code>{r['url']}</code></td>"
        f"</tr>"
        for r in rows
    )
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="robots" content="noindex">
  <title>Stable Link Index</title>
</head>
<body>
  <h1>Stable Link Index</h1>
  <p>All stable page IDs registered in this site.</p>
  <table>
    <thead>
      <tr><th>ID</th><th>Title</th><th>URL</th></tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""
