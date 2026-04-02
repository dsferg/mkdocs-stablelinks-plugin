"""Tests for macros plugin ordering check."""

import logging
import pytest
from unittest.mock import MagicMock

from mkdocs_stablelinks.compat import check_macros_order


def _make_config(plugin_names):
    """Build a minimal MkDocs config dict with an ordered plugins mapping."""
    # Use a plain dict — insertion order preserved in Python 3.7+
    plugins = {name: MagicMock() for name in plugin_names}
    return {"plugins": plugins}


def test_no_macros_no_warning(caplog):
    config = _make_config(["stablelinks"])
    with caplog.at_level(logging.WARNING):
        check_macros_order(config)
    assert caplog.text == ""


def test_macros_before_stablelinks_no_warning(caplog):
    config = _make_config(["macros", "stablelinks"])
    with caplog.at_level(logging.WARNING):
        check_macros_order(config)
    assert caplog.text == ""


def test_macros_after_stablelinks_warns(caplog):
    config = _make_config(["stablelinks", "macros"])
    with caplog.at_level(logging.WARNING):
        check_macros_order(config)
    assert "mkdocs-macros-plugin is installed but listed after" in caplog.text


def test_macros_after_stablelinks_with_other_plugins_warns(caplog):
    config = _make_config(["search", "stablelinks", "other", "macros"])
    with caplog.at_level(logging.WARNING):
        check_macros_order(config)
    assert "mkdocs-macros-plugin is installed but listed after" in caplog.text
