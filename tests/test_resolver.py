"""Tests for id: link resolution."""

import pytest
from unittest.mock import MagicMock
from mkdocs.exceptions import PluginError

from mkdocs_stablelinks.index import IDIndex, PageEntry
from mkdocs_stablelinks.resolver import resolve_links, _relative_md_path


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
