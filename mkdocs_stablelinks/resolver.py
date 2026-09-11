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

# Matches a reference link definition whose destination is an id:, e.g.
#   [ref]: id:page-id#anchor "Optional title"
# Python-Markdown strips these lines and resolves [text][ref] against them,
# so the destination has to be rewritten here or it reaches the output as a
# literal href="id:page-id".
_REF_DEF_RE = re.compile(
    r"^(?P<indent>[ ]{0,3})\[(?P<label>[^\]\n]+)\]:[ \t]*"
    r"id:(?P<id>[A-Za-z0-9-]+)(?P<anchor>#\S*)?"
    r"(?P<title>[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^)\n]*\)))?[ \t]*$",
    re.MULTILINE,
)

# Matches fenced code blocks (``` or ~~~) and inline code (`...`)
_CODE_BLOCK_RE = re.compile(
    r"(`{3,}|~{3,}).*?\1|`[^`\n]+`",
    re.DOTALL,
)

_SENTINEL_RE = re.compile(r"\x00STABLELINKS(\d+)\x00")

# A list item marker: '-', '*', '+', or '1.'. Python-Markdown, which MkDocs
# uses, does not treat '1)' as a list marker, so neither do we — counting one
# as a list would wrongly raise the indent needed for a code block after it.
_LIST_MARKER_RE = re.compile(r"^[ ]*(?:[-*+]|\d{1,9}\.)[ \t]+")

_TAB_WIDTH = 4


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
    # Both link forms contain the literal "id:", so a page without it has
    # nothing to resolve and needs none of the work below — which is most
    # pages on most sites, on every rebuild during `mkdocs serve`.
    if "id:" not in markdown:
        return markdown

    current_src = page.file.src_path.replace("\\", "/")  # normalise Windows paths

    # Replace code with placeholders so its contents are not processed, then
    # restore them after substitution. Fenced and inline code go first, so a
    # fence's contents cannot be mistaken for an indented code block.
    placeholders: list[str] = []

    def _stash(text: str) -> str:
        placeholders.append(text)
        return f"\x00STABLELINKS{len(placeholders) - 1}\x00"

    protected = _CODE_BLOCK_RE.sub(lambda m: _stash(m.group(0)), markdown)
    protected = _stash_indented_code(protected, _stash)

    unresolved: list[str] = []

    def _resolve(page_id: str) -> str | None:
        """Return the relative path for page_id, recording it if unresolved."""
        entry = index.resolve(page_id)
        if entry is not None:
            return _relative_md_path(current_src, entry.src_path)

        if on_unresolved == "error":
            unresolved.append(page_id)
        else:
            log.warning(
                "mkdocs-stablelinks: Unresolved id '%s' in %s — "
                "no page declares this id.",
                page_id,
                current_src,
            )
        return None

    def _replace_inline(m: re.Match) -> str:
        rel_path = _resolve(m.group(2))
        if rel_path is None:
            # Preserve original syntax rather than emitting a broken link
            return m.group(0)
        return f"[{m.group(1)}]({rel_path}{m.group(3) or ''})"

    def _replace_ref_def(m: re.Match) -> str:
        rel_path = _resolve(m.group("id"))
        if rel_path is None:
            return m.group(0)
        anchor = m.group("anchor") or ""
        title = m.group("title") or ""
        return f"{m.group('indent')}[{m.group('label')}]: {rel_path}{anchor}{title}"

    result = _LINK_RE.sub(_replace_inline, protected)
    result = _REF_DEF_RE.sub(_replace_ref_def, result)

    result = _restore_placeholders(result, placeholders)

    if unresolved:
        ids = ", ".join(f"'{i}'" for i in dict.fromkeys(unresolved))
        raise PluginError(
            f"mkdocs-stablelinks: Unresolved id(s) {ids} in {current_src} — "
            "no page declares these ids."
        )

    return result


def _restore_placeholders(text: str, placeholders: list[str]) -> str:
    """
    Put stashed code back.

    Stashed text can itself contain a sentinel — an indented code block holding
    an inline code span, for instance — so restoration repeats until nothing
    changes. The pass count is bounded by the number of placeholders, and
    out-of-range indices (which would only appear if the source markdown
    contained a literal sentinel) are left untouched rather than crashing.
    """
    if not placeholders:
        return text

    def _sub(m: re.Match) -> str:
        idx = int(m.group(1))
        if 0 <= idx < len(placeholders):
            return placeholders[idx]
        return m.group(0)

    for _ in range(len(placeholders)):
        restored = _SENTINEL_RE.sub(_sub, text)
        if restored == text:
            break
        text = restored

    return text


def _indent_width(line: str) -> int:
    """Width of a line's leading whitespace, with tabs expanded."""
    expanded = line.expandtabs(_TAB_WIDTH)
    return len(expanded) - len(expanded.lstrip(" "))


def _stash_indented_code(text: str, stash) -> str:
    """
    Replace indented (4-space) code blocks with placeholders.

    A run of lines indented four or more columns past the enclosing block,
    following a blank line, is an indented code block. Tracking the enclosing
    list keeps ordinary list continuation paragraphs — which are indented but
    are not code — available for link resolution.
    """
    lines = text.split("\n")
    out: list[str] = []
    # Content indents of the list items currently open, outermost first.
    list_indents: list[int] = []
    prev_blank = True
    i = 0

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            out.append(line)
            prev_blank = True
            i += 1
            continue

        expanded = line.expandtabs(_TAB_WIDTH)
        indent = len(expanded) - len(expanded.lstrip(" "))

        # Leaving a list item's content closes it.
        while list_indents and indent < list_indents[-1]:
            list_indents.pop()

        base = list_indents[-1] if list_indents else 0

        if _LIST_MARKER_RE.match(expanded) and indent <= base + 3:
            # Python-Markdown indents list item content by a fixed four
            # columns, whatever the marker's width, so code inside an item
            # starts at eight rather than at marker width plus four.
            list_indents.append(base + 4)
            out.append(line)
            prev_blank = False
            i += 1
            continue

        if prev_blank and indent >= base + 4:
            block: list[str] = []
            while i < len(lines):
                candidate = lines[i]
                if not candidate.strip() or _indent_width(candidate) < base + 4:
                    break
                block.append(candidate)
                i += 1
            out.append(stash("\n".join(block)))
            prev_blank = False
            continue

        out.append(line)
        prev_blank = False
        i += 1

    return "\n".join(out)


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
