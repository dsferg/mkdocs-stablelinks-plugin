"""ID index construction and lookup."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from .validators import validate_and_register

log = logging.getLogger("mkdocs.plugins.stablelinks")


@dataclass
class PageEntry:
    page_id: str
    src_path: str
    url: Optional[str] = None
    title: Optional[str] = None


class IDIndex:
    """Holds the mapping from page ID → PageEntry."""

    def __init__(self) -> None:
        # page_id → PageEntry
        self._entries: Dict[str, PageEntry] = {}
        # src_path → page_id (to look up entries by source file)
        self._by_src: Dict[str, str] = {}

    def build(self, files: Files) -> None:
        """
        Scan all pages' front matter and populate the index.

        Called during on_files, which fires on every rebuild (including
        during mkdocs serve), ensuring the index stays current.
        """
        self._entries.clear()
        self._by_src.clear()

        # Registry maps page_id → src_path for duplicate detection
        registry: Dict[str, str] = {}

        for file in files.documentation_pages():
            src_path = _normalize(file.src_path)
            abs_path = file.abs_src_path
            if abs_path is None:
                continue

            page_id = _extract_id(abs_path, src_path)
            if page_id is None:
                continue

            if validate_and_register(page_id, src_path, registry):
                entry = PageEntry(page_id=page_id, src_path=src_path)
                self._entries[page_id] = entry
                self._by_src[src_path] = page_id

    def populate_url(self, src_path: str, url: str) -> None:
        page_id = self._by_src.get(_normalize(src_path))
        if page_id is not None:
            self._entries[page_id].url = url

    def populate_title(self, src_path: str, title: Optional[str]) -> None:
        page_id = self._by_src.get(_normalize(src_path))
        if page_id is not None:
            self._entries[page_id].title = title

    def resolve(self, page_id: str) -> Optional[PageEntry]:
        return self._entries.get(page_id)

    def all_entries(self) -> List[PageEntry]:
        return sorted(self._entries.values(), key=lambda e: e.page_id)

    def __len__(self) -> int:
        return len(self._entries)


def _normalize(src_path: str) -> str:
    """Normalise OS path separators to forward slashes."""
    return src_path.replace("\\", "/")


def _extract_id(abs_path: str, src_path: str) -> Optional[str]:
    """Read front matter from a markdown file and return the id field, or None."""
    try:
        with open(abs_path, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    # Find the closing ---
    end = content.find("\n---", 3)
    if end == -1:
        return None

    front_matter_text = content[3:end].strip()
    try:
        data = yaml.safe_load(front_matter_text)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    page_id = data.get("id")
    if page_id is None:
        return None

    return str(page_id)
