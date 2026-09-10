"""Tests for ID index construction."""

from unittest.mock import MagicMock

import pytest
from mkdocs.exceptions import PluginError
from mkdocs.structure.files import File

from mkdocs_stablelinks.index import IDIndex, _extract_id, _read_source


def _make_file(tmp_path, rel_path, content, encoding="utf-8"):
    """Write a real source file and wrap it in a real MkDocs File."""
    full = tmp_path / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding=encoding)
    return File(rel_path, str(tmp_path), str(tmp_path / "site"), use_directory_urls=True)


def _make_files(tmp_path, specs):
    """
    specs: list of (rel_path, front_matter) tuples.
    Returns a mock Files object whose documentation_pages() yields real Files.
    """
    file_objs = [
        _make_file(tmp_path, rel_path, f"---\n{fm}\n---\n\n# Content\n")
        for rel_path, fm in specs
    ]

    files = MagicMock()
    files.documentation_pages.return_value = file_objs
    return files


class TestExtractId:
    def test_extracts_id(self):
        assert _extract_id("---\nid: my-page\ntitle: My Page\n---\n\n# Content\n") == "my-page"

    def test_no_front_matter(self):
        assert _extract_id("# No front matter here\n") is None

    def test_front_matter_no_id(self):
        assert _extract_id("---\ntitle: Only a title\n---\n\n# Content\n") is None

    def test_id_as_number_coerced_to_string(self):
        assert _extract_id("---\nid: 42\n---\n") == "42"

    def test_unclosed_front_matter(self):
        assert _extract_id("---\nid: my-page\n# no closing delimiter\n") is None

    def test_malformed_yaml(self):
        assert _extract_id("---\nid: [unclosed\n---\n\n# Content\n") is None

    def test_dots_terminator(self):
        # MkDocs accepts '...' as a front matter terminator, so the index
        # must too, or the id is silently dropped on a page that builds fine.
        assert _extract_id("---\nid: my-page\n...\n\n# Content\n") == "my-page"

    def test_front_matter_far_beyond_8kb(self):
        # Large front matter must still be parsed. MkDocs reads the whole
        # source file regardless, so there is nothing to gain by giving up.
        padding = "padding: " + "x" * 8200 + "\n"
        assert _extract_id(f"---\nid: my-page\n{padding}---\n\n# Content\n") == "my-page"


class TestReadSource:
    def test_reads_file_from_disk(self, tmp_path):
        f = _make_file(tmp_path, "page.md", "---\nid: my-page\n---\n")
        assert _read_source(f) == "---\nid: my-page\n---\n"

    def test_utf8_bom_is_stripped(self, tmp_path):
        # MkDocs reads sources as utf-8-sig, so a page with a BOM builds
        # normally. The index must see the same front matter or the id is
        # silently dropped and every link to it fails to resolve.
        f = _make_file(tmp_path, "page.md", "---\nid: my-page\n---\n", encoding="utf-8-sig")
        assert _extract_id(_read_source(f)) == "my-page"

    def test_missing_file(self, tmp_path):
        f = File("ghost.md", str(tmp_path), str(tmp_path / "site"), use_directory_urls=True)
        assert _read_source(f) is None

    def test_undecodable_file_skipped(self, tmp_path):
        full = tmp_path / "page.md"
        full.write_bytes(b"---\nid: \xff\xfe not utf-8\n---\n")
        f = File("page.md", str(tmp_path), str(tmp_path / "site"), use_directory_urls=True)
        assert _read_source(f) is None

    def test_generated_in_memory_file(self, tmp_path):
        # Plugins such as mkdocs-gen-files produce files with no path on
        # disk. Their front matter must be indexed like any other page's.
        f = File.generated(
            MagicMock(), "generated.md", content="---\nid: gen-page\n---\n\n# Generated\n"
        )
        assert f.abs_src_path is None
        assert _extract_id(_read_source(f)) == "gen-page"


class TestIDIndex:
    def test_builds_index(self, tmp_path):
        files = _make_files(tmp_path, [
            ("install/windows.md", "id: install-windows"),
            ("index.md", "title: Home"),  # no id
        ])
        index = IDIndex()
        index.build(files)
        assert len(index) == 1
        entry = index.resolve("install-windows")
        assert entry is not None
        assert entry.src_path == "install/windows.md"

    def test_duplicate_id_raises(self, tmp_path):
        files = _make_files(tmp_path, [
            ("a.md", "id: same-id"),
            ("b.md", "id: same-id"),
        ])
        index = IDIndex()
        with pytest.raises(PluginError, match="Duplicate id 'same-id'"):
            index.build(files)

    def test_invalid_id_not_registered(self, tmp_path, caplog):
        files = _make_files(tmp_path, [("page.md", "id: Bad_ID")])
        index = IDIndex()
        index.build(files)
        assert len(index) == 0
        assert "Invalid id" in caplog.text

    def test_populate_url_and_title(self, tmp_path):
        files = _make_files(tmp_path, [("page.md", "id: my-page")])
        index = IDIndex()
        index.build(files)
        index.populate_url("page.md", "/page/")
        index.populate_title("page.md", "My Page")

        entry = index.resolve("my-page")
        assert entry.url == "/page/"
        assert entry.title == "My Page"

    def test_all_entries_sorted(self, tmp_path):
        files = _make_files(tmp_path, [
            ("b.md", "id: zebra"),
            ("a.md", "id: apple"),
            ("c.md", "id: mango"),
        ])
        index = IDIndex()
        index.build(files)
        ids = [e.page_id for e in index.all_entries()]
        assert ids == sorted(ids)

    def test_rebuild_clears_stale_entries(self, tmp_path):
        files_v1 = _make_files(tmp_path, [("page.md", "id: old-id")])
        index = IDIndex()
        index.build(files_v1)
        assert index.resolve("old-id") is not None

        files_v2 = _make_files(tmp_path, [("page.md", "id: new-id")])
        index.build(files_v2)
        assert index.resolve("old-id") is None
        assert index.resolve("new-id") is not None

    def test_unreadable_files_skipped(self, tmp_path):
        missing = File("ghost.md", str(tmp_path), str(tmp_path / "site"), True)
        files = MagicMock()
        files.documentation_pages.return_value = [missing]

        index = IDIndex()
        index.build(files)
        assert len(index) == 0

    def test_indexes_generated_in_memory_file(self, tmp_path):
        generated = File.generated(
            MagicMock(), "generated.md", content="---\nid: gen-page\n---\n\n# Generated\n"
        )
        on_disk = _make_file(tmp_path, "page.md", "---\nid: disk-page\n---\n")
        files = MagicMock()
        files.documentation_pages.return_value = [generated, on_disk]

        index = IDIndex()
        index.build(files)
        assert len(index) == 2
        assert index.resolve("gen-page").src_path == "generated.md"
