"""Main plugin class and MkDocs hook implementations."""

import logging
import os
from typing import Optional

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from .compat import check_macros_order
from .config import StablelinksConfig
from .index import IDIndex
from .index_page import generate_index_page
from .redirects import generate_html_redirects, generate_netlify_redirects
from .resolver import resolve_links

log = logging.getLogger("mkdocs.plugins.stablelinks")


class StablelinksPlugin(BasePlugin[StablelinksConfig]):

    def __init__(self) -> None:
        super().__init__()
        self._index = IDIndex()

    # ------------------------------------------------------------------
    # on_config
    # ------------------------------------------------------------------

    def on_config(self, config: MkDocsConfig) -> Optional[MkDocsConfig]:
        """Check macros plugin ordering and protected path collisions."""
        check_macros_order(config)
        self._check_path_collision(config)
        return config

    # ------------------------------------------------------------------
    # on_files
    # ------------------------------------------------------------------

    def on_files(self, files: Files, config: MkDocsConfig) -> Files:
        """
        Build the ID index from all pages' front matter.

        on_files fires on every rebuild (including during mkdocs serve),
        so the index stays current when files change.
        """
        self._index = IDIndex()
        self._index.build(files)
        log.debug("mkdocs-stablelinks: Indexed %d page IDs.", len(self._index))
        return files

    def _check_path_collision(self, config: MkDocsConfig) -> None:
        redirect_path = self.config["redirect_path"]
        docs_dir = config["docs_dir"]
        collision_path = os.path.join(docs_dir, redirect_path)
        if os.path.exists(collision_path):
            log.warning(
                "mkdocs-stablelinks: redirect_path '%s' conflicts with an "
                "existing directory in docs_dir. Redirect pages may overwrite "
                "existing content.",
                redirect_path,
            )

    # ------------------------------------------------------------------
    # on_page_markdown
    # ------------------------------------------------------------------

    def on_page_markdown(
        self,
        markdown: str,
        page: Page,
        config: MkDocsConfig,
        files: Files,
    ) -> str:
        """Resolve id: links in page markdown."""
        # Populate the URL for this page now that MkDocs has computed it
        self._index.populate_url(page.file.src_path, page.url)
        return resolve_links(
            markdown,
            page,
            self._index,
            self.config["on_unresolved"],
        )

    # ------------------------------------------------------------------
    # on_page_context
    # ------------------------------------------------------------------

    def on_page_context(self, context, page: Page, config: MkDocsConfig, nav):
        """Populate page titles in the ID index."""
        self._index.populate_title(page.file.src_path, page.title)
        return context

    # ------------------------------------------------------------------
    # on_post_build
    # ------------------------------------------------------------------

    def on_post_build(self, config: MkDocsConfig) -> None:
        """Generate redirect pages and the index page."""
        site_dir = config["site_dir"]
        redirect_path = self.config["redirect_path"]
        mechanism = self.config["redirect_mechanism"]

        if mechanism in ("html", "both"):
            generate_html_redirects(self._index, redirect_path, site_dir)

        if mechanism in ("netlify", "both"):
            generate_netlify_redirects(self._index, redirect_path, site_dir)

        if self.config["index_page"]:
            generate_index_page(self._index, redirect_path, site_dir)
