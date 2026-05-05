from pathlib import Path
from .path_utils import PathUtils
from .log_utils import LogUtils


class PromptUtils:
    """Load Markdown prompt templates and fill variables via str.format()."""

    _cache: dict[str, str] = {}

    @classmethod
    def load(cls, name: str, **kwargs) -> str:
        if name not in cls._cache:
            prompt_path = PathUtils.get_abs_path(f"config/prompts/{name}.md")
            if not prompt_path.exists():
                LogUtils.error(f"Prompt file not found: {prompt_path}")
                return ""
            cls._cache[name] = prompt_path.read_text(encoding="utf-8")

        template = cls._cache[name]
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                LogUtils.warning(f"Missing prompt variable: {e}")
                return template
        return template

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
