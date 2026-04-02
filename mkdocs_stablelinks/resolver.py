"""id: link resolution in markdown."""

import logging
import os
import re

from mkdocs.exceptions import PluginError
from mkdocs.structure.pages import Page

from .index import IDIndex

log = logging.getLogger("mkdocs.plugins.stablelinks")

# Matches [text](id:page-id) and [text](id:page-id#anchor)
_LINK_RE = re.compile(r"\[([^\]]*)\]\(id:([A-Za-z0-9-]+)(#[^)]*)?\)")

# Matches fenced code blocks (``` or ~~~) and inline code (`...`)
_CODE_BLOCK_RE = re.compile(
    r"(`{3,}|~{3,}).*?\1|`[^`\n]+`",
    re.DOTALL,
)


def resolve_links(
    markdown: str,
    page: Page,
    index: IDIndex,
    on_unresolved: str,
) -> str:
    """
    Replace id: links in markdown with relative .md paths.

    MkDocs converts relative .md paths in markdown to the correct output URLs,
    so we produce paths like '../install/windows.md' rather than output URLs.

    on_unresolved: 'warn' or 'error'
    """
    current_src = page.file.src_path.replace("\\", "/")  # normalise Windows paths

    # Replace code blocks with placeholders so their contents are not processed,
    # then restore them after substitution.
    placeholders: list = []

    def _stash_code(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f"\x00STABLELINKS{len(placeholders) - 1}\x00"

    protected = _CODE_BLOCK_RE.sub(_stash_code, markdown)

    unresolved: list = []

    def _replace(m: re.Match) -> str:
        text = m.group(1)
        page_id = m.group(2)
        anchor = m.group(3) or ""

        entry = index.resolve(page_id)
        if entry is None:
            if on_unresolved == "error":
                unresolved.append(page_id)
            else:
                log.warning(
                    "mkdocs-stablelinks: Unresolved id '%s' in %s — "
                    "no page declares this id.",
                    page_id,
                    current_src,
                )
            # Preserve original syntax rather than emitting a broken link
            return m.group(0)

        rel_path = _relative_md_path(current_src, entry.src_path)
        return f"[{text}]({rel_path}{anchor})"

    result = _LINK_RE.sub(_replace, protected)

    # Restore stashed code blocks
    for i, code in enumerate(placeholders):
        result = result.replace(f"\x00STABLELINKS{i}\x00", code)

    if unresolved:
        ids = ", ".join(f"'{i}'" for i in unresolved)
        raise PluginError(
            f"mkdocs-stablelinks: Unresolved id(s) {ids} in {current_src} — "
            "no page declares these ids."
        )

    return result


def _relative_md_path(from_src: str, to_src: str) -> str:
    """
    Compute a relative path from one markdown source file to another.

    Both paths are relative to the docs directory (e.g. 'a/b.md', 'c/d.md').
    Returns a path like '../c/d.md' suitable for use in markdown links.
    """
    from_dir = os.path.dirname(from_src)
    # os.path.relpath uses OS separators; normalise to forward slashes
    rel = os.path.relpath(to_src, from_dir)
    return rel.replace("\\", "/")
