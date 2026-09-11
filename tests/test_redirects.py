"""Tests for redirect page generation."""


from mkdocs_stablelinks.index import IDIndex, PageEntry
from mkdocs_stablelinks.redirects import generate_html_redirects


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

    def test_subpath_url_prefix(self, tmp_path):
        """Sites hosted under a sub-path get the prefix on redirect targets."""
        index = _make_index([("my-page", "page.md", "page/")])
        generate_html_redirects(index, "go", str(tmp_path), url_prefix="/repo")

        content = (tmp_path / "go" / "my-page" / "index.html").read_text()
        assert 'url=/repo/page/' in content
        assert 'href="/repo/page/"' in content


class TestHtmlRedirectLineEndings:
    def test_redirect_pages_always_use_lf(self, tmp_path):
        index = _make_index([("my-page", "page.md", "/page/")])
        generate_html_redirects(index, "go", str(tmp_path))

        raw = (tmp_path / "go" / "my-page" / "index.html").read_bytes()
        assert b"\r\n" not in raw
