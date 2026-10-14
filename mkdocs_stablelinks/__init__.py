"""mkdocs-stablelinks-plugin — stable internal linking for MkDocs."""

from importlib.metadata import PackageNotFoundError, version

try:
    # Read the version from installed package metadata so pyproject.toml
    # stays the single source of truth and the two cannot drift apart.
    __version__ = version("mkdocs-stablelinks-plugin")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0+unknown"
