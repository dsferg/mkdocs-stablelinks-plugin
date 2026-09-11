"""Integration tests for StablelinksPlugin hook behaviour."""

from unittest.mock import MagicMock

from mkdocs.structure.files import File, Files, InclusionLevel

from mkdocs_stablelinks.index import PageEntry
from mkdocs_stablelinks.plugin import StablelinksPlugin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin(**config_overrides):
    plugin = StablelinksPlugin()
    plugin.config = {
        "redirect_path": "go",
        "index_page": True,
        "on_unresolved": "warn",
        **config_overrides,
    }
    return plugin


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
    def test_accepts_valid_config(self, tmp_path):
        config = _make_mkdocs_config(str(tmp_path), str(tmp_path / "site"))
        plugin = _make_plugin(redirect_path="go")
        assert plugin.on_config(config) is config


# ---------------------------------------------------------------------------
# on_files
# ---------------------------------------------------------------------------

def _make_files(tmp_path, specs, use_directory_urls=True):
    """
    specs: list of (rel_path, front_matter or None) tuples.
    Returns a real Files collection over real source files.
    """
    file_objs = []
    for rel_path, fm in specs:
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        body = f"---\n{fm}\n---\n# Content\n" if fm else "# Content\n"
        full.write_text(body)
        file_objs.append(
            File(rel_path, str(tmp_path), str(tmp_path / "site"), use_directory_urls)
        )
    return Files(file_objs)


class TestOnFiles:
    def _make_files(self, tmp_path, specs):
        return _make_files(tmp_path, specs)

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
# Path collision detection
# ---------------------------------------------------------------------------

class TestPathCollisions:
    def _run(self, tmp_path, specs, use_directory_urls=True, **config_overrides):
        files = _make_files(tmp_path, specs, use_directory_urls)
        config = _make_mkdocs_config(str(tmp_path), str(tmp_path / "site"))
        plugin = _make_plugin(redirect_path="go", **config_overrides)
        plugin.on_files(files, config)
        return plugin

    def test_page_overwritten_by_index_page(self, tmp_path, caplog):
        # docs/go.md builds to go/index.html — exactly where the generated
        # ID index page is written. No 'go' directory exists in docs_dir,
        # so a source-path check misses this entirely.
        self._run(tmp_path, [("go.md", None), ("index.md", "id: home")])
        assert "'go.md' builds to 'go/index.html'" in caplog.text
        assert "will overwrite it" in caplog.text

    def test_index_page_in_redirect_dir_overwritten(self, tmp_path, caplog):
        self._run(tmp_path, [("go/index.md", None), ("index.md", "id: home")])
        assert "'go/index.md' builds to 'go/index.html'" in caplog.text

    def test_page_overwritten_by_redirect_page(self, tmp_path, caplog):
        # A page whose output path matches a generated redirect for id 'alpha'.
        self._run(tmp_path, [("page.md", "id: alpha"), ("go/alpha/index.md", None)])
        assert "'go/alpha/index.md' builds to 'go/alpha/index.html'" in caplog.text

    def test_content_inside_redirect_path_warns_without_overwrite(self, tmp_path, caplog):
        self._run(tmp_path, [("go/other.md", None)])
        assert "1 file(s) build into redirect_path 'go'" in caplog.text
        assert "will overwrite it" not in caplog.text

    def test_many_inside_files_are_summarised(self, tmp_path, caplog):
        specs = [(f"go/p{n}.md", None) for n in range(8)]
        self._run(tmp_path, specs)
        assert "8 file(s) build into redirect_path 'go'" in caplog.text
        assert "and 3 more" in caplog.text

    def test_no_overwrite_warning_when_no_ids_registered(self, tmp_path, caplog):
        # With no IDs anywhere, generate_index_page writes nothing, so a page
        # at go.md survives and must not be reported as overwritten.
        self._run(tmp_path, [("go.md", None), ("index.md", None)])
        assert "will overwrite it" not in caplog.text
        assert "build into redirect_path 'go'" in caplog.text

    def test_no_warning_without_collision(self, tmp_path, caplog):
        self._run(tmp_path, [("index.md", "id: home"), ("going-further.md", None)])
        assert caplog.text == ""

    def test_no_warning_when_directory_urls_disabled(self, tmp_path, caplog):
        # Without directory URLs, docs/go.md builds to go.html, which does
        # not collide with the generated go/index.html.
        self._run(tmp_path, [("go.md", None)], use_directory_urls=False)
        assert caplog.text == ""

    def test_index_page_disabled_downgrades_to_inside_warning(self, tmp_path, caplog):
        self._run(tmp_path, [("go.md", None)], index_page=False)
        assert "will overwrite it" not in caplog.text
        assert "build into redirect_path 'go'" in caplog.text

    def test_excluded_files_are_not_reported(self, tmp_path, caplog):
        files = _make_files(tmp_path, [("go.md", None)])
        for f in files:
            f.inclusion = InclusionLevel.EXCLUDED
        config = _make_mkdocs_config(str(tmp_path), str(tmp_path / "site"))
        _make_plugin(redirect_path="go").on_files(files, config)
        assert caplog.text == ""


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

    def test_index_page_disabled(self, tmp_path):
        plugin = _make_plugin(index_page=False)
        entry = PageEntry(page_id="pg", src_path="p.md", url="/p/", title="P")
        plugin._index._entries["pg"] = entry

        config = MagicMock()
        config.__getitem__ = lambda self, key: str(tmp_path) if key == "site_dir" else None

        plugin.on_post_build(config)
        assert not (tmp_path / "go" / "index.html").exists()
