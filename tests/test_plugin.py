"""Integration tests for StablelinksPlugin hook behaviour."""

import os
import textwrap
import pytest
from unittest.mock import MagicMock, patch

from mkdocs_stablelinks.plugin import StablelinksPlugin
from mkdocs_stablelinks.index import PageEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin(**config_overrides):
    plugin = StablelinksPlugin()
    plugin.config = {
        "redirect_path": "go",
        "redirect_mechanism": "both",
        "index_page": True,
        "on_unresolved": "warn",
        **config_overrides,
    }
    return plugin


def _make_file(src_path, abs_src_path, url):
    f = MagicMock()
    f.src_path = src_path
    f.abs_src_path = abs_src_path
    f.dest_uri = url
    return f


def _make_page(src_path, url, title="Test Page"):
    page = MagicMock()
    page.file.src_path = src_path
    page.url = url
    page.title = title
    return page


def _make_mkdocs_config(docs_dir, site_dir):
    config = MagicMock()
    config.__getitem__ = lambda self, key: {
        "docs_dir": docs_dir,
        "site_dir": site_dir,
        "plugins": {"stablelinks": MagicMock()},
    }[key]
    config.__contains__ = lambda self, key: key in {
        "docs_dir", "site_dir", "plugins"
    }
    return config


# ---------------------------------------------------------------------------
# on_config
# ---------------------------------------------------------------------------

class TestOnConfig:
    def test_warns_on_path_collision(self, tmp_path, caplog):
        (tmp_path / "go").mkdir()
        config = _make_mkdocs_config(str(tmp_path), str(tmp_path / "site"))

        plugin = _make_plugin(redirect_path="go")
        plugin.on_config(config)

        assert "conflicts with an existing directory" in caplog.text


# ---------------------------------------------------------------------------
# on_files
# ---------------------------------------------------------------------------

class TestOnFiles:
    def _make_files(self, tmp_path, specs):
        file_mocks = []
        for rel_path, fm in specs:
            full = tmp_path / rel_path
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(f"---\n{fm}\n---\n# Content\n")
            m = MagicMock()
            m.src_path = rel_path
            m.abs_src_path = str(full)
            file_mocks.append(m)
        files = MagicMock()
        files.documentation_pages.return_value = file_mocks
        return files

    def test_builds_index(self, tmp_path):
        files = self._make_files(tmp_path, [("page.md", "id: my-page")])
        config = _make_mkdocs_config(str(tmp_path), str(tmp_path / "site"))

        plugin = _make_plugin()
        plugin.on_files(files, config)

        assert plugin._index.resolve("my-page") is not None

    def test_rebuilds_on_each_call(self, tmp_path):
        d1 = tmp_path / "v1"
        d2 = tmp_path / "v2"
        files_v1 = self._make_files(d1, [("page.md", "id: old-id")])
        files_v2 = self._make_files(d2, [("page.md", "id: new-id")])
        config = _make_mkdocs_config(str(tmp_path), str(tmp_path / "site"))

        plugin = _make_plugin()
        plugin.on_files(files_v1, config)
        assert plugin._index.resolve("old-id") is not None

        plugin.on_files(files_v2, config)
        assert plugin._index.resolve("old-id") is None
        assert plugin._index.resolve("new-id") is not None


# ---------------------------------------------------------------------------
# on_page_markdown
# ---------------------------------------------------------------------------

class TestOnPageMarkdown:
    def _plugin_with_entry(self, page_id, src_path, url):
        plugin = _make_plugin()
        entry = PageEntry(page_id=page_id, src_path=src_path, url=url)
        plugin._index._entries[page_id] = entry
        plugin._index._by_src[src_path] = page_id
        return plugin

    def test_resolves_id_link(self):
        plugin = self._plugin_with_entry(
            "target-page", "target.md", "/target/"
        )
        page = _make_page("source.md", "/source/")
        config = MagicMock()
        files = MagicMock()

        md = "[Go there](id:target-page)"
        result = plugin.on_page_markdown(md, page=page, config=config, files=files)
        assert "id:target-page" not in result
        assert "[Go there]" in result

    def test_preserves_unresolved_link(self, caplog):
        plugin = _make_plugin()
        page = _make_page("source.md", "/source/")

        md = "[Missing](id:does-not-exist)"
        result = plugin.on_page_markdown(md, page=page, config=MagicMock(), files=MagicMock())
        assert result == "[Missing](id:does-not-exist)"


# ---------------------------------------------------------------------------
# on_page_context
# ---------------------------------------------------------------------------

class TestOnPageContext:
    def test_populates_title(self):
        plugin = _make_plugin()
        entry = PageEntry(page_id="my-page", src_path="page.md")
        plugin._index._entries["my-page"] = entry
        plugin._index._by_src["page.md"] = "my-page"

        page = _make_page("page.md", "/page/", title="My Page")
        plugin.on_page_context(MagicMock(), page=page, config=MagicMock(), nav=MagicMock())

        assert plugin._index.resolve("my-page").title == "My Page"


# ---------------------------------------------------------------------------
# on_post_build
# ---------------------------------------------------------------------------

class TestOnPostBuild:
    def _plugin_with_entry(self, page_id, src_path, url, title="Page"):
        plugin = _make_plugin()
        entry = PageEntry(page_id=page_id, src_path=src_path, url=url, title=title)
        plugin._index._entries[page_id] = entry
        plugin._index._by_src[src_path] = page_id
        return plugin

    def test_generates_html_redirect(self, tmp_path):
        plugin = self._plugin_with_entry("my-page", "page.md", "/page/")
        config = MagicMock()
        config.__getitem__ = lambda self, key: str(tmp_path) if key == "site_dir" else None

        plugin.on_post_build(config)
        assert (tmp_path / "go" / "my-page" / "index.html").exists()

    def test_generates_netlify_redirects(self, tmp_path):
        plugin = self._plugin_with_entry("my-page", "page.md", "/page/")
        config = MagicMock()
        config.__getitem__ = lambda self, key: str(tmp_path) if key == "site_dir" else None

        plugin.on_post_build(config)
        content = (tmp_path / "_redirects").read_text()
        assert "/go/my-page/ /page/ 301" in content

    def test_html_only_mechanism(self, tmp_path):
        plugin = _make_plugin(redirect_mechanism="html")
        entry = PageEntry(page_id="pg", src_path="p.md", url="/p/")
        plugin._index._entries["pg"] = entry

        config = MagicMock()
        config.__getitem__ = lambda self, key: str(tmp_path) if key == "site_dir" else None

        plugin.on_post_build(config)
        assert (tmp_path / "go" / "pg" / "index.html").exists()
        assert not (tmp_path / "_redirects").exists()

    def test_netlify_only_mechanism(self, tmp_path):
        plugin = _make_plugin(redirect_mechanism="netlify")
        entry = PageEntry(page_id="pg", src_path="p.md", url="/p/")
        plugin._index._entries["pg"] = entry

        config = MagicMock()
        config.__getitem__ = lambda self, key: str(tmp_path) if key == "site_dir" else None

        plugin.on_post_build(config)
        assert not (tmp_path / "go" / "pg").exists()
        assert (tmp_path / "_redirects").exists()

    def test_index_page_disabled(self, tmp_path):
        plugin = _make_plugin(index_page=False)
        entry = PageEntry(page_id="pg", src_path="p.md", url="/p/", title="P")
        plugin._index._entries["pg"] = entry

        config = MagicMock()
        config.__getitem__ = lambda self, key: str(tmp_path) if key == "site_dir" else None

        plugin.on_post_build(config)
        assert not (tmp_path / "go" / "index.html").exists()
