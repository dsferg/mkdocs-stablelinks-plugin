"""Tests for ID index page generation."""

import pytest

from mkdocs_stablelinks.index import IDIndex, PageEntry
from mkdocs_stablelinks.index_page import generate_index_page


def _make_index(entries):
    """entries: list of (page_id, src_path, url, title)"""
    index = IDIndex()
    for page_id, src_path, url, title in entries:
        entry = PageEntry(page_id=page_id, src_path=src_path, url=url, title=title)
        index._entries[page_id] = entry
        index._by_src[src_path] = page_id
    return index


class TestGenerateIndexPage:
    def test_creates_index_file(self, tmp_path):
        index = _make_index([("my-page", "page.md", "/page/", "My Page")])
        generate_index_page(index, "go", str(tmp_path))
        assert (tmp_path / "go" / "index.html").exists()

    def test_contains_id_and_title(self, tmp_path):
        index = _make_index([("my-page", "page.md", "/page/", "My Page")])
        generate_index_page(index, "go", str(tmp_path))

        content = (tmp_path / "go" / "index.html").read_text()
        assert "my-page" in content
        assert "My Page" in content
        assert "/page/" in content

    def test_noindex_meta_present(self, tmp_path):
        index = _make_index([("api", "api.md", "/api/", "API")])
        generate_index_page(index, "go", str(tmp_path))

        content = (tmp_path / "go" / "index.html").read_text()
        assert "noindex" in content

    def test_falls_back_to_id_when_no_title(self, tmp_path):
        index = _make_index([("my-page", "page.md", "/page/", None)])
        generate_index_page(index, "go", str(tmp_path))

        content = (tmp_path / "go" / "index.html").read_text()
        assert "my-page" in content

    def test_empty_index_creates_no_file(self, tmp_path):
        index = _make_index([])
        generate_index_page(index, "go", str(tmp_path))
        assert not (tmp_path / "go" / "index.html").exists()

    def test_skips_entry_without_url(self, tmp_path):
        index = _make_index([("no-url", "page.md", None, "No URL")])
        generate_index_page(index, "go", str(tmp_path))
        assert not (tmp_path / "go" / "index.html").exists()

    def test_custom_redirect_path(self, tmp_path):
        index = _make_index([("api", "api.md", "/api/", "API")])
        generate_index_page(index, "links", str(tmp_path))
        assert (tmp_path / "links" / "index.html").exists()
