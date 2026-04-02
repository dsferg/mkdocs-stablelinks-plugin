from mkdocs.config import config_options
from mkdocs.config.base import Config


class StablelinksConfig(Config):
    redirect_path = config_options.Type(str, default="go")
    redirect_mechanism = config_options.Choice(
        ("html", "netlify", "both"), default="both"
    )
    index_page = config_options.Type(bool, default=True)
    on_unresolved = config_options.Choice(("warn", "error"), default="warn")
