"""ID format validation and duplicate detection."""

import re
import logging
from typing import Dict, Optional

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
    Emits warnings/errors via logging on failure.
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
        log.error(
            "mkdocs-stablelinks: Duplicate id '%s' found in:\n"
            "  %s\n"
            "  %s\n"
            "Each id must be unique across the site.",
            page_id,
            registry[page_id],
            src_path,
        )
        return False

    registry[page_id] = src_path
    return True
