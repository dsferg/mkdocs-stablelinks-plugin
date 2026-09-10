from mkdocs.config import config_options
from mkdocs.config.base import Config


class StablelinksConfig(Config):
    redirect_path = config_options.Type(str, default="go")
    index_page = config_options.Type(bool, default=True)
    on_unresolved = config_options.Choice(("warn", "error"), default="warn")
