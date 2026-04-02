"""Tests for redirect page generation."""

import os
import pytest

from mkdocs_stablelinks.index import IDIndex, PageEntry
from mkdocs_stablelinks.redirects import generate_html_redirects, generate_netlify_redirects


def _make_index(entries):
    """entries: list of (page_id, src_path, url)"""
    index = IDIndex()
    for page_id, src_path, url in entries:
        entry = PageEntry(page_id=page_id, src_path=src_path, url=url)
        index._entries[page_id] = entry
        index._by_src[src_path] = page_id
    return index


class TestHtmlRedirects:
    def test_creates_redirect_file(self, tmp_path):
        index = _make_index([("install-windows", "install/windows.md", "/install/windows/")])
        generate_html_redirects(index, "go", str(tmp_path))

        out = tmp_path / "go" / "install-windows" / "index.html"
        assert out.exists()
        content = out.read_text()
        assert 'content="0; url=/install/windows/"' in content
        assert 'href="/install/windows/"' in content

    def test_url_without_leading_slash(self, tmp_path):
        index = _make_index([("my-page", "page.md", "page/")])
        generate_html_redirects(index, "go", str(tmp_path))

        content = (tmp_path / "go" / "my-page" / "index.html").read_text()
        assert 'url=/page/' in content

    def test_canonical_link_present(self, tmp_path):
        index = _make_index([("api", "api.md", "/api/")])
        generate_html_redirects(index, "go", str(tmp_path))

        content = (tmp_path / "go" / "api" / "index.html").read_text()
        assert 'rel="canonical"' in content

    def test_skips_entry_without_url(self, tmp_path, caplog):
        index = _make_index([("no-url", "page.md", None)])
        # url=None — should skip without crashing
        generate_html_redirects(index, "go", str(tmp_path))
        assert not (tmp_path / "go" / "no-url").exists()

    def test_multiple_redirects(self, tmp_path):
        index = _make_index([
            ("page-a", "a.md", "/a/"),
            ("page-b", "b.md", "/b/"),
        ])
        generate_html_redirects(index, "go", str(tmp_path))
        assert (tmp_path / "go" / "page-a" / "index.html").exists()
        assert (tmp_path / "go" / "page-b" / "index.html").exists()

    def test_custom_redirect_path(self, tmp_path):
        index = _make_index([("my-page", "page.md", "/page/")])
        generate_html_redirects(index, "links", str(tmp_path))
        assert (tmp_path / "links" / "my-page" / "index.html").exists()


class TestNetlifyRedirects:
    def test_creates_redirects_file(self, tmp_path):
        index = _make_index([("install-windows", "install/windows.md", "/install/windows/")])
        generate_netlify_redirects(index, "go", str(tmp_path))

        redirects_file = tmp_path / "_redirects"
        assert redirects_file.exists()
        content = redirects_file.read_text()
        assert "/go/install-windows/ /install/windows/ 301" in content

    def test_includes_header_comment(self, tmp_path):
        index = _make_index([("api", "api.md", "/api/")])
        generate_netlify_redirects(index, "go", str(tmp_path))

        content = (tmp_path / "_redirects").read_text()
        assert "# mkdocs-stablelinks" in content

    def test_appends_to_existing_file(self, tmp_path):
        existing = tmp_path / "_redirects"
        existing.write_text("/old/ /new/ 301\n")

        index = _make_index([("my-page", "page.md", "/page/")])
        generate_netlify_redirects(index, "go", str(tmp_path))

        content = existing.read_text()
        assert "/old/ /new/ 301" in content
        assert "/go/my-page/ /page/ 301" in content

    def test_empty_index_writes_nothing(self, tmp_path):
        index = _make_index([])
        generate_netlify_redirects(index, "go", str(tmp_path))
        assert not (tmp_path / "_redirects").exists()

    def test_skips_entry_without_url(self, tmp_path):
        index = _make_index([("no-url", "page.md", None)])
        generate_netlify_redirects(index, "go", str(tmp_path))
        # File may or may not exist, but must not contain the id
        redirects_file = tmp_path / "_redirects"
        if redirects_file.exists():
            assert "no-url" not in redirects_file.read_text()
