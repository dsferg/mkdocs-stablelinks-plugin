"""Tests for ID validation."""

import pytest
from mkdocs.exceptions import PluginError
from mkdocs_stablelinks.validators import is_valid_id, validate_and_register


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
