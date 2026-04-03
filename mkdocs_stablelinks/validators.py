"""ID format validation and duplicate detection."""

import re
import logging
from typing import Dict

from mkdocs.exceptions import PluginError

log = logging.getLogger("mkdocs.plugins.stablelinks")

_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def is_valid_id(page_id: str) -> bool:
    """Return True if page_id meets format requirements."""
    return bool(_ID_PATTERN.match(page_id))


def validate_and_register(
    page_id: str,
    src_path: str,
    registry: Dict[str, str],
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
