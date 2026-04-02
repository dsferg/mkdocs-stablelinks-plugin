"""mkdocs-macros-plugin compatibility check."""

import logging

from mkdocs.config.defaults import MkDocsConfig

log = logging.getLogger("mkdocs.plugins.stablelinks")

_WARNING = (
    "mkdocs-stablelinks: mkdocs-macros-plugin is installed but listed after "
    "mkdocs-stablelinks in mkdocs.yml. Include tags inside snippet files may "
    "not resolve correctly. Move macros before stablelinks in your plugins list."
)


def check_macros_order(config: MkDocsConfig) -> None:
    """
    Warn if mkdocs-macros-plugin appears after stablelinks in the plugins list.

    The plugins mapping preserves insertion order (Python 3.7+), so we can
    check relative position by converting keys to a list.
    """
    plugin_names = list(config["plugins"].keys())

    if "macros" not in plugin_names:
        return

    try:
        macros_idx = plugin_names.index("macros")
        stablelinks_idx = plugin_names.index("stablelinks")
    except ValueError:
        return

    if macros_idx > stablelinks_idx:
        log.warning(_WARNING)
