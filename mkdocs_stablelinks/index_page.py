"""ID index page generation."""

import html as html_lib
import logging
import os
import types
from typing import List, Optional

from .index import IDIndex

log = logging.getLogger("mkdocs.plugins.stablelinks")


def generate_index_page(
    index: IDIndex,
    redirect_path: str,
    site_dir: str,
    config,
    nav,
    env,
) -> None:
    """
    Write the ID index page to <site_dir>/<redirect_path>/index.html.

    Renders using the site theme when possible, falling back to bare HTML.
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

    content_html = _build_content_html(rows)
    page_url = f"/{redirect_path}/"

    html = _render_with_theme(content_html, page_url, redirect_path, config, nav, env)
    if html is None:
        html = _build_bare_html(content_html)

    out_dir = os.path.join(site_dir, redirect_path)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)


def _render_with_theme(
    content_html: str,
    page_url: str,
    redirect_path: str,
    config,
    nav,
    env,
) -> Optional[str]:
    """
    Render the index page using the MkDocs theme's Jinja2 template.

    Returns None if rendering fails so the caller can fall back to bare HTML.
    """
    if env is None:
        return None

    try:
        template = env.get_template("main.html")
    except Exception:
        return None

    # Depth of the page in the URL hierarchy determines how many levels
    # to traverse to reach the site root (used for relative asset URLs).
    depth = len([p for p in redirect_path.split("/") if p])
    base_url = "/".join([".."] * depth) if depth else "."

    page = types.SimpleNamespace(
        title="Stable Link Index",
        content=content_html,
        # search: exclude prevents this page appearing in site search
        meta={"search": {"exclude": True}},
        toc=[],
        url=page_url,
        abs_url=page_url,
        canonical_url=page_url,
        edit_url=None,
        is_homepage=False,
        previous_page=None,
        next_page=None,
        markdown="",
        file=types.SimpleNamespace(
            src_path=f"{redirect_path}/index.md",
            dest_uri=f"{redirect_path}/index.html",
        ),
    )

    try:
        return template.render(
            config=config,
            page=page,
            nav=nav,
            base_url=base_url,
        )
    except Exception as exc:
        log.debug(
            "mkdocs-stablelinks: Could not render index page with theme (%s); "
            "falling back to bare HTML.",
            exc,
        )
        return None


def _build_content_html(rows: List[dict]) -> str:
    table_rows = "\n      ".join(
        f"<tr>"
        f"<td><code>{html_lib.escape(r['id'])}</code></td>"
        f"<td><a href=\"{html_lib.escape(r['url'])}\">{html_lib.escape(r['title'])}</a></td>"
        f"<td><code>{html_lib.escape(r['url'])}</code></td>"
        f"</tr>"
        for r in rows
    )
    return (
        "<h1>Stable Link Index</h1>\n"
        "<p>All stable page IDs registered in this site.</p>\n"
        "<table>\n"
        "  <thead>\n"
        "    <tr><th>ID</th><th>Title</th><th>URL</th></tr>\n"
        "  </thead>\n"
        "  <tbody>\n"
        f"    {table_rows}\n"
        "  </tbody>\n"
        "</table>"
    )


def _build_bare_html(content_html: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="robots" content="noindex">\n'
        "  <title>Stable Link Index</title>\n"
        "</head>\n"
        "<body>\n"
        f"{content_html}\n"
        "</body>\n"
        "</html>\n"
    )
