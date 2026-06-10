"""Shared utilities."""

from urllib.parse import urlsplit


def url_prefix(site_url: str | None) -> str:
    """Return the path component of site_url, for prefixing absolute URLs.

    Sites hosted under a sub-path (e.g. https://user.github.io/repo/) need
    redirect targets like '/repo/install/windows/', not '/install/windows/'.
    Returns '' when site_url is unset or the site is hosted at the domain root.
    """
    if not site_url:
        return ""
    return urlsplit(site_url).path.rstrip("/")


def absolute_url(prefix: str, url: str) -> str:
    """Join a site path prefix and a site-root-relative URL into an absolute path."""
    if not url.startswith("/"):
        url = f"/{url}"
    return f"{prefix}{url}"
