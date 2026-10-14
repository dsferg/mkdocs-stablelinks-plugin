"""ID index construction and lookup."""

from dataclasses import dataclass

from mkdocs.structure.files import Files
from mkdocs.utils.meta import get_data

from .validators import validate_and_register


@dataclass
class PageEntry:
    page_id: str
    src_path: str
    url: str | None = None
    title: str | None = None


class IDIndex:
    """Holds the mapping from page ID → PageEntry."""

    def __init__(self) -> None:
        # page_id → PageEntry
        self._entries: dict[str, PageEntry] = {}
        # src_path → page_id (to look up entries by source file)
        self._by_src: dict[str, str] = {}

    def build(self, files: Files) -> None:
        """
        Scan all pages' front matter and populate the index.

        Called during on_files, which fires on every rebuild (including
        during mkdocs serve), ensuring the index stays current.
        """
        self._entries.clear()
        self._by_src.clear()

        # Registry maps page_id → src_path for duplicate detection
        registry: dict[str, str] = {}

        for file in files.documentation_pages():
            src_path = _normalize(file.src_path)

            content = _read_source(file)
            if content is None:
                continue

            page_id = _extract_id(content)
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

    def populate_title(self, src_path: str, title: str | None) -> None:
        page_id = self._by_src.get(_normalize(src_path))
        if page_id is not None:
            self._entries[page_id].title = title

    def resolve(self, page_id: str) -> PageEntry | None:
        return self._entries.get(page_id)

    def all_entries(self) -> list[PageEntry]:
        return sorted(self._entries.values(), key=lambda e: e.page_id)

    def __len__(self) -> int:
        return len(self._entries)


def _normalize(src_path: str) -> str:
    """Normalise OS path separators to forward slashes."""
    return src_path.replace("\\", "/")


def _read_source(file) -> str | None:
    """Return a file's source text, or None if it cannot be read."""
    try:
        # content_string decodes as utf-8-sig, so a byte-order mark does not
        # hide the front matter, and it also covers files that other plugins
        # generate in memory, which have no path on disk.
        return file.content_string
    except (OSError, ValueError):
        # Unreadable or undecodable. MkDocs reports the failure itself when
        # it reads the same file, so stay quiet here.
        return None


def _extract_id(content: str) -> str | None:
    """Return the id declared in a document's front matter, or None.

    Parsing is delegated to MkDocs' own front-matter reader so the index sees
    exactly the metadata MkDocs puts on page.meta — including front matter
    closed with '...' rather than '---'.
    """
    _, data = get_data(content)

    page_id = data.get("id")
    if page_id is None:
        return None

    return str(page_id)
