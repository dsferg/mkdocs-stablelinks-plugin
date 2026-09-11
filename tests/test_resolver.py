"""Tests for id: link resolution."""

from unittest.mock import MagicMock

import pytest
from mkdocs.exceptions import PluginError

from mkdocs_stablelinks.index import IDIndex, PageEntry
from mkdocs_stablelinks.resolver import _relative_md_path, resolve_links


def _make_page(src_path, url):
    page = MagicMock()
    page.file.src_path = src_path
    page.url = url
    return page


def _make_index(entries):
    """entries: list of (page_id, src_path, url)"""
    index = IDIndex()
    for page_id, src_path, url in entries:
        entry = PageEntry(page_id=page_id, src_path=src_path, url=url)
        index._entries[page_id] = entry
        index._by_src[src_path] = page_id
    return index


class TestRelativeMdPath:
    def test_same_dir(self):
        assert _relative_md_path("docs/a.md", "docs/b.md") == "b.md"

    def test_parent_dir(self):
        result = _relative_md_path("docs/sub/a.md", "docs/b.md")
        assert result == "../b.md"

    def test_sibling_dir(self):
        result = _relative_md_path("docs/a/page.md", "docs/b/page.md")
        assert result == "../b/page.md"

    def test_root_to_nested(self):
        result = _relative_md_path("index.md", "install/windows.md")
        assert result == "install/windows.md"


class TestResolveLinks:
    def test_resolves_simple_link(self):
        index = _make_index([("install-windows", "install/windows.md", "/install/windows/")])
        page = _make_page("getting-started/index.md", "/getting-started/")

        md = "[Install on Windows](id:install-windows)"
        result = resolve_links(md, page, index, "warn")
        assert "[Install on Windows](../install/windows.md)" == result

    def test_resolves_link_with_anchor(self):
        index = _make_index([("install-windows", "install/windows.md", "/install/windows/")])
        page = _make_page("getting-started/index.md", "/getting-started/")

        md = "[Install](id:install-windows#prerequisites)"
        result = resolve_links(md, page, index, "warn")
        assert result == "[Install](../install/windows.md#prerequisites)"

    def test_unresolved_warn_preserves_original(self, caplog):
        index = _make_index([])
        page = _make_page("index.md", "/")

        md = "[Missing](id:no-such-page)"
        result = resolve_links(md, page, index, "warn")
        assert result == "[Missing](id:no-such-page)"
        assert "Unresolved id" in caplog.text

    def test_unresolved_error_raises(self):
        index = _make_index([])
        page = _make_page("index.md", "/")

        with pytest.raises(PluginError, match="no-such-page"):
            resolve_links("[Missing](id:no-such-page)", page, index, "error")

    def test_non_id_links_untouched(self):
        index = _make_index([])
        page = _make_page("index.md", "/")

        md = "[External](https://example.com) and [relative](../other.md)"
        result = resolve_links(md, page, index, "warn")
        assert result == md

    def test_id_link_inside_fenced_code_block_untouched(self):
        index = _make_index([("my-page", "page.md", "/page/")])
        page = _make_page("index.md", "/")

        md = "```\n[link](id:my-page)\n```"
        result = resolve_links(md, page, index, "warn")
        assert result == md

    def test_id_link_inside_inline_code_untouched(self):
        index = _make_index([("my-page", "page.md", "/page/")])
        page = _make_page("index.md", "/")

        md = "Use `[link](id:my-page)` as an example."
        result = resolve_links(md, page, index, "warn")
        assert result == md

    def test_id_link_outside_code_block_still_resolved(self):
        index = _make_index([("my-page", "page.md", "/page/")])
        page = _make_page("index.md", "/")

        md = "```\n[link](id:my-page)\n```\n\n[real](id:my-page)"
        result = resolve_links(md, page, index, "warn")
        assert "```\n[link](id:my-page)\n```" in result
        assert "[real](page.md)" in result

    def test_multiple_code_blocks_restored_correctly(self):
        index = _make_index([("my-page", "page.md", "/page/")])
        page = _make_page("index.md", "/")

        md = (
            "```python\nprint('hello')\n```\n\n"
            "[real link](id:my-page)\n\n"
            "```js\nconsole.log('hi')\n```\n\n"
            "Some `inline code` here.\n\n"
            "~~~\nanother fence\n~~~"
        )
        result = resolve_links(md, page, index, "warn")
        # The link should be resolved
        assert "[real link](page.md)" in result
        # All code blocks should be preserved verbatim
        assert "```python\nprint('hello')\n```" in result
        assert "```js\nconsole.log('hi')\n```" in result
        assert "`inline code`" in result
        assert "~~~\nanother fence\n~~~" in result

    def test_stray_sentinel_in_source_is_preserved(self):
        """A literal placeholder sentinel in source markdown that points
        outside the placeholder list must not crash the build."""
        index = _make_index([("my-page", "page.md", "/page/")])
        page = _make_page("index.md", "/")

        # Inline code stashes one placeholder (index 0); the bare sentinel
        # for index 99 has no corresponding entry and must be left as-is.
        md = "`code` and a stray \x00STABLELINKS99\x00 marker"
        result = resolve_links(md, page, index, "warn")
        assert "`code`" in result
        assert "\x00STABLELINKS99\x00" in result


class TestIndentedCodeBlocks:
    """Four-space indented code must be protected, but indented list
    continuations — which look the same to a naive check — must not be."""

    def _resolve(self, md, on_unresolved="warn"):
        index = _make_index([("alpha", "target.md", "/target/")])
        return resolve_links(md, _make_page("index.md", "/"), index, on_unresolved)

    def test_indented_code_block_preserved(self):
        result = self._resolve("Intro:\n\n    [x](id:alpha)\n")
        assert "    [x](id:alpha)" in result

    def test_tab_indented_code_block_preserved(self):
        result = self._resolve("Intro:\n\n\t[x](id:alpha)\n")
        assert "id:alpha" in result

    def test_indented_code_with_inline_code_preserved(self):
        # The stashed block contains an inline-code placeholder, so restoring
        # it has to handle a sentinel nested inside stashed text.
        result = self._resolve("Intro:\n\n    a `b` and [x](id:alpha)\n")
        assert "    a `b` and [x](id:alpha)" in result

    def test_blank_separated_indented_chunks_preserved(self):
        md = "Intro:\n\n    [a](id:alpha)\n\n    [b](id:alpha)\n"
        result = self._resolve(md)
        assert "    [a](id:alpha)" in result
        assert "    [b](id:alpha)" in result

    def test_ordered_list_continuation_resolves(self):
        md = "1. Step\n\n    See [x](id:alpha).\n\n2. Next\n"
        result = self._resolve(md)
        assert "[x](target.md)" in result

    def test_bullet_list_continuation_resolves(self):
        md = "- Item\n\n  See [x](id:alpha).\n"
        result = self._resolve(md)
        assert "[x](target.md)" in result

    def test_nested_list_item_resolves(self):
        md = "- Outer\n    - Inner [x](id:alpha)\n"
        result = self._resolve(md)
        assert "[x](target.md)" in result

    def test_code_block_inside_list_preserved(self):
        md = "- Item\n\n        [x](id:alpha)\n"
        result = self._resolve(md)
        assert "        [x](id:alpha)" in result

    def test_indented_line_without_preceding_blank_resolves(self):
        # A lazy continuation of a paragraph is not a code block.
        md = "Some text\n    and [x](id:alpha) more\n"
        result = self._resolve(md)
        assert "[x](target.md)" in result

    def test_dedent_after_list_restores_top_level_code(self):
        md = "- Item\n\nBack at top level:\n\n    [x](id:alpha)\n"
        result = self._resolve(md)
        assert "    [x](id:alpha)" in result

    def test_unresolved_id_in_indented_code_does_not_warn(self, caplog):
        self._resolve("Intro:\n\n    [x](id:nope)\n")
        assert caplog.text == ""


class TestReferenceDefinitions:
    def _resolve(self, md, on_unresolved="warn"):
        index = _make_index([("alpha", "target.md", "/target/")])
        return resolve_links(md, _make_page("index.md", "/"), index, on_unresolved)

    def test_reference_definition_resolved(self):
        result = self._resolve("See [y][ref].\n\n[ref]: id:alpha\n")
        assert "[ref]: target.md" in result
        assert "id:alpha" not in result

    def test_anchor_preserved(self):
        result = self._resolve("[ref]: id:alpha#section\n")
        assert "[ref]: target.md#section" in result

    def test_title_preserved(self):
        result = self._resolve('[ref]: id:alpha "A title"\n')
        assert '[ref]: target.md "A title"' in result

    def test_single_quoted_title_preserved(self):
        result = self._resolve("[ref]: id:alpha 'A title'\n")
        assert "[ref]: target.md 'A title'" in result

    def test_leading_indent_preserved(self):
        result = self._resolve("   [ref]: id:alpha\n")
        assert "   [ref]: target.md" in result

    def test_definition_in_code_block_preserved(self):
        result = self._resolve("Intro:\n\n    [ref]: id:alpha\n")
        assert "    [ref]: id:alpha" in result

    def test_unresolved_definition_warns_and_preserves(self, caplog):
        result = self._resolve("[ref]: id:nope\n")
        assert "[ref]: id:nope" in result
        assert "Unresolved id 'nope'" in caplog.text

    def test_unresolved_definition_errors_when_configured(self):
        with pytest.raises(PluginError, match="'nope'"):
            self._resolve("[ref]: id:nope\n", on_unresolved="error")

    def test_not_a_definition_when_indented_four_spaces_inline(self):
        # Four or more spaces makes it a code block, not a definition.
        result = self._resolve("Text\n\n    [ref]: id:alpha\n")
        assert "id:alpha" in result

    def test_inline_and_reference_both_resolved(self):
        md = "[a](id:alpha) and [b][ref]\n\n[ref]: id:alpha\n"
        result = self._resolve(md)
        assert "[a](target.md)" in result
        assert "[ref]: target.md" in result


class TestEarlyExit:
    def test_markdown_without_id_is_returned_unchanged(self):
        index = _make_index([("alpha", "target.md", "/target/")])
        md = "# Title\n\n    indented code\n\n- list\n\n`code` and [a](other.md)\n"
        result = resolve_links(md, _make_page("index.md", "/"), index, "warn")
        assert result == md

    def test_early_exit_does_not_skip_reference_definitions(self):
        # The ref-def form also contains "id:", so the shortcut must not
        # cause it to be missed.
        index = _make_index([("alpha", "target.md", "/target/")])
        result = resolve_links("[r]: id:alpha\n", _make_page("index.md", "/"), index, "warn")
        assert "[r]: target.md" in result


class TestListIndentMatchesPythonMarkdown:
    """Python-Markdown indents list content by a fixed four columns whatever
    the marker's width, and does not accept '1)' as a marker. The scanner has
    to agree, or it protects links that should resolve and vice versa."""

    def _resolve(self, md):
        index = _make_index([("alpha", "target.md", "/target/")])
        return resolve_links(md, _make_page("index.md", "/"), index, "warn")

    def test_six_spaces_in_bullet_is_continuation_not_code(self):
        # Marker width would put code at six columns; Python-Markdown needs eight.
        result = self._resolve("- item\n\n      [x](id:alpha)\n")
        assert "[x](target.md)" in result

    def test_eight_spaces_in_bullet_is_code(self):
        result = self._resolve("- item\n\n        [x](id:alpha)\n")
        assert "id:alpha" in result

    def test_eight_spaces_under_wide_marker_is_code(self):
        # '2026. ' is six columns wide, but content still indents by four.
        result = self._resolve("2026. item\n\n        [x](id:alpha)\n")
        assert "id:alpha" in result

    def test_paren_marker_does_not_open_a_list(self):
        # Python-Markdown renders '1) paren' as a paragraph, so the indented
        # block after it is a plain code block.
        result = self._resolve("1) paren\n\n    [x](id:alpha)\n")
        assert "id:alpha" in result
