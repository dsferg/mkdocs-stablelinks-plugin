"""ID format validation and duplicate detection."""

import logging
import os
import re

from mkdocs.exceptions import PluginError

log = logging.getLogger("mkdocs.plugins.stablelinks")

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_REDIRECT_PATH_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*(/[a-z0-9_-]+)*$")


def is_valid_id(page_id: str) -> bool:
    """Return True if page_id meets format requirements."""
    return bool(_ID_PATTERN.match(page_id))


def validate_and_register(
    page_id: str,
    src_path: str,
    registry: dict[str, str],
) -> bool:
    """
    Validate page_id and register it in registry if valid and not duplicate.

    Returns True if registration succeeded.
    Warns via logging if the ID format is invalid.
    Raises PluginError if the ID is a duplicate.
    """
    if not is_valid_id(page_id):
        log.warning(
            "mkdocs-stablelinks: Invalid id '%s' in %s — "
            "IDs must contain only lowercase letters, numbers, and hyphens.",
            page_id,
            src_path,
        )
        return False

    if page_id in registry:
        raise PluginError(
            f"mkdocs-stablelinks: Duplicate id '{page_id}' found in:\n"
            f"  {registry[page_id]}\n"
            f"  {src_path}\n"
            "Each id must be unique across the site."
        )

    registry[page_id] = src_path
    return True


def validate_redirect_path(redirect_path: str, site_dir: str) -> None:
    """
    Verify that redirect_path contains only safe characters and resolves
    to a location inside site_dir.

    Raises PluginError if the path contains unsafe characters or would
    escape the output directory.
    """
    if not _REDIRECT_PATH_PATTERN.match(redirect_path):
        raise PluginError(
            f"mkdocs-stablelinks: redirect_path '{redirect_path}' contains "
            "invalid characters. Only lowercase letters, numbers, hyphens, "
            "underscores, and forward slashes are allowed."
        )

    resolved_site = os.path.realpath(site_dir)
    resolved_dest = os.path.realpath(os.path.join(site_dir, redirect_path))
    if not resolved_dest.startswith(resolved_site + os.sep) and resolved_dest != resolved_site:
        raise PluginError(
            f"mkdocs-stablelinks: redirect_path '{redirect_path}' resolves to "
            f"'{resolved_dest}', which is outside the site directory "
            f"'{resolved_site}'. Use a relative path that stays within the "
            "output directory."
        )
