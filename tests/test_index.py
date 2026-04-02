"""Tests for ID index construction."""

import pytest
from unittest.mock import MagicMock

from mkdocs_stablelinks.index import IDIndex, _extract_id


def _make_files(tmp_path, specs):
    """
    specs: list of (rel_path, front_matter) tuples.
    Returns a mock Files object whose documentation_pages() yields file mocks.
    """
    file_mocks = []
    for rel_path, fm in specs:
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(f"---\n{fm}\n---\n\n# Content\n")
        m = MagicMock()
        m.src_path = rel_path
        m.abs_src_path = str(full)
        file_mocks.append(m)

    files = MagicMock()
    files.documentation_pages.return_value = file_mocks
    return files


class TestExtractId:
    def test_extracts_id(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("---\nid: my-page\ntitle: My Page\n---\n\n# Content\n")
        assert _extract_id(str(f), "page.md") == "my-page"

    def test_no_front_matter(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("# No front matter here\n")
        assert _extract_id(str(f), "page.md") is None

    def test_front_matter_no_id(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("---\ntitle: Only a title\n---\n\n# Content\n")
        assert _extract_id(str(f), "page.md") is None

    def test_missing_file(self, tmp_path):
        assert _extract_id(str(tmp_path / "ghost.md"), "ghost.md") is None

    def test_id_as_number_coerced_to_string(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("---\nid: 42\n---\n")
        assert _extract_id(str(f), "page.md") == "42"

    def test_unclosed_front_matter(self, tmp_path):
        f = tmp_path / "page.md"
        f.write_text("---\nid: my-page\n# no closing delimiter\n")
        assert _extract_id(str(f), "page.md") is None


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

    def test_duplicate_id_not_registered(self, tmp_path, caplog):
        files = _make_files(tmp_path, [
            ("a.md", "id: same-id"),
            ("b.md", "id: same-id"),
        ])
        index = IDIndex()
        index.build(files)
        assert len(index) == 1
        assert "Duplicate id" in caplog.text

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

    def test_non_markdown_files_skipped(self, tmp_path):
        m = MagicMock()
        m.src_path = "image.png"
        m.abs_src_path = str(tmp_path / "image.png")
        files = MagicMock()
        files.documentation_pages.return_value = [m]

        index = IDIndex()
        index.build(files)
        assert len(index) == 0
