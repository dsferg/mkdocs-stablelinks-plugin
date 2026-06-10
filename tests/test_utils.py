"""Tests for shared utilities."""

from mkdocs_stablelinks.utils import absolute_url, url_prefix


class TestUrlPrefix:
    def test_none_site_url(self):
        assert url_prefix(None) == ""

    def test_empty_site_url(self):
        assert url_prefix("") == ""

    def test_domain_root(self):
        assert url_prefix("https://example.com/") == ""

    def test_domain_root_no_trailing_slash(self):
        assert url_prefix("https://example.com") == ""

    def test_subpath(self):
        assert url_prefix("https://user.github.io/repo/") == "/repo"

    def test_subpath_no_trailing_slash(self):
        assert url_prefix("https://user.github.io/repo") == "/repo"

    def test_nested_subpath(self):
        assert url_prefix("https://example.com/docs/v2/") == "/docs/v2"


class TestAbsoluteUrl:
    def test_no_prefix(self):
        assert absolute_url("", "page/") == "/page/"

    def test_no_prefix_leading_slash(self):
        assert absolute_url("", "/page/") == "/page/"

    def test_prefix(self):
        assert absolute_url("/repo", "page/") == "/repo/page/"

    def test_prefix_leading_slash(self):
        assert absolute_url("/repo", "/page/") == "/repo/page/"

    def test_homepage_url(self):
        assert absolute_url("/repo", "") == "/repo/"
