"""Tests for ID validation."""

import os

import pytest
from mkdocs.exceptions import PluginError

from mkdocs_stablelinks.validators import (
    is_valid_id,
    validate_and_register,
    validate_redirect_path,
)


@pytest.mark.parametrize("page_id", [
    "install-windows",
    "getting-started",
    "api",
    "v2",
    "my-page-123",
])
def test_valid_ids(page_id):
    assert is_valid_id(page_id) is True


@pytest.mark.parametrize("page_id", [
    "Install-Windows",   # uppercase
    "install windows",  # space
    "-start",           # leading hyphen
    "hello_world",      # underscore
    "",                 # empty
    "hello!",           # special char
])
def test_invalid_ids(page_id):
    assert is_valid_id(page_id) is False


def test_register_success():
    registry = {}
    result = validate_and_register("my-page", "docs/page.md", registry)
    assert result is True
    assert registry == {"my-page": "docs/page.md"}


def test_register_duplicate():
    registry = {"my-page": "docs/original.md"}
    with pytest.raises(PluginError, match="Duplicate id 'my-page'"):
        validate_and_register("my-page", "docs/duplicate.md", registry)


def test_register_invalid_format(caplog):
    registry = {}
    result = validate_and_register("Bad_ID", "docs/page.md", registry)
    assert result is False
    assert registry == {}
    assert "Invalid id" in caplog.text


# --- validate_redirect_path ---


def test_redirect_path_valid(tmp_path):
    site_dir = str(tmp_path / "site")
    os.makedirs(site_dir, exist_ok=True)
    # Should not raise for normal relative paths
    validate_redirect_path("go", site_dir)
    validate_redirect_path("stable/links", site_dir)
    validate_redirect_path("my_links-2", site_dir)


def test_redirect_path_traversal(tmp_path):
    site_dir = str(tmp_path / "site")
    os.makedirs(site_dir, exist_ok=True)
    with pytest.raises(PluginError, match="invalid characters"):
        validate_redirect_path("../../etc", site_dir)


def test_redirect_path_absolute(tmp_path):
    site_dir = str(tmp_path / "site")
    os.makedirs(site_dir, exist_ok=True)
    with pytest.raises(PluginError, match="invalid characters"):
        validate_redirect_path("/tmp/evil", site_dir)


@pytest.mark.parametrize("bad_path", [
    "go links",        # space
    "go\nlinks",       # newline
    "GO",              # uppercase
    "go!",             # special character
    "go links\t301",   # tab
    "go/",             # trailing slash
    "go//links",       # double slash
    "go/links/",       # trailing slash after segment
])
def test_redirect_path_invalid_characters(tmp_path, bad_path):
    site_dir = str(tmp_path / "site")
    os.makedirs(site_dir, exist_ok=True)
    with pytest.raises(PluginError, match="invalid characters"):
        validate_redirect_path(bad_path, site_dir)
