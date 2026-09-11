"""Main plugin class and MkDocs hook implementations."""

import logging

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from .compat import check_macros_order
from .config import StablelinksConfig
from .index import IDIndex
from .index_page import generate_index_page
from .redirects import generate_html_redirects
from .resolver import resolve_links
from .utils import url_prefix
from .validators import validate_redirect_path

log = logging.getLogger("mkdocs.plugins.stablelinks")


class StablelinksPlugin(BasePlugin[StablelinksConfig]):

    def __init__(self) -> None:
        super().__init__()
        self._index = IDIndex()
        self._env = None
        self._nav = None

    # ------------------------------------------------------------------
    # on_config
    # ------------------------------------------------------------------

    def on_config(self, config: MkDocsConfig) -> MkDocsConfig | None:
        """Validate redirect_path and check macros ordering."""
        validate_redirect_path(self.config["redirect_path"], config["site_dir"])
        check_macros_order(config)
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
        self._check_path_collisions(files)
        return files

    def _generated_dest_uris(self) -> set[str]:
        """Output paths this plugin will write during on_post_build."""
        redirect_path = self.config["redirect_path"]
        generated = set()

        # The index page is only written when at least one ID is registered,
        # so a site that has not adopted any IDs yet must not be warned that
        # its own page at <redirect_path>/ will be overwritten.
        if self.config["index_page"] and len(self._index) > 0:
            generated.add(f"{redirect_path}/index.html")

        for entry in self._index.all_entries():
            generated.add(f"{redirect_path}/{entry.page_id}/index.html")

        return generated

    def _check_path_collisions(self, files: Files) -> None:
        """
        Warn when site content is built into the redirect path.

        Compares against build *output* paths rather than source paths: a
        page at docs/go.md builds to 'go/index.html' and is overwritten by
        the generated index page, even though no 'go' directory exists in
        docs_dir.
        """
        redirect_path = self.config["redirect_path"]
        prefix = f"{redirect_path}/"
        generated = self._generated_dest_uris()

        overwritten: list[tuple[str, str]] = []
        inside: list[str] = []

        for file in files:
            # Excluded files are never written, so they cannot collide.
            if not file.inclusion.is_included():
                continue

            if file.dest_uri in generated:
                overwritten.append((file.src_uri, file.dest_uri))
            elif file.dest_uri.startswith(prefix):
                inside.append(file.src_uri)

        for src_uri, dest_uri in sorted(overwritten):
            log.warning(
                "mkdocs-stablelinks: '%s' builds to '%s', which mkdocs-stablelinks "
                "also generates. The generated page will overwrite it. Move the "
                "page, or set redirect_path to a path the site does not use.",
                src_uri,
                dest_uri,
            )

        if inside:
            shown = sorted(inside)
            listing = ", ".join(shown[:5])
            if len(shown) > 5:
                listing += f", and {len(shown) - 5} more"
            log.warning(
                "mkdocs-stablelinks: %d file(s) build into redirect_path '%s', "
                "which is reserved for generated redirect pages: %s. Move them, "
                "or set redirect_path to a path the site does not use.",
                len(shown),
                redirect_path,
                listing,
            )

    # ------------------------------------------------------------------
    # on_env / on_nav
    # ------------------------------------------------------------------

    def on_env(self, env, config: MkDocsConfig, files: Files):
        """Store the Jinja2 environment for use in on_post_build."""
        self._env = env
        return env

    def on_nav(self, nav, config: MkDocsConfig, files: Files):
        """Store the navigation for use in on_post_build."""
        self._nav = nav
        return nav

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
        # Sites hosted under a sub-path (e.g. GitHub Pages project sites)
        # need that sub-path prepended to absolute redirect URLs.
        prefix = url_prefix(config["site_url"])

        generate_html_redirects(self._index, redirect_path, site_dir, prefix)

        if self.config["index_page"]:
            generate_index_page(
                self._index, redirect_path, site_dir, config, self._nav, self._env, prefix
            )
