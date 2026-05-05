# 提示词工具模块 —— 加载 Markdown 模板并使用 str.format() 填充变量。
from pathlib import Path
from .path_utils import PathUtils
from .log_utils import LogUtils


class PromptUtils:
    """Load Markdown prompt templates and fill variables via str.format()."""

    # 模板缓存：key 为模板名，value 为模板原文（含 { } 占位符）。
    _cache: dict[str, str] = {}

    @classmethod
    def load(cls, name: str, **kwargs) -> str:
        """加载指定名称的 Markdown 提示词模板，并用 kwargs 填充占位符。

        Args:
            name: 模板文件名（不含 .md 扩展名），对应 config/prompts/{name}.md。
            **kwargs: 传递给 str.format() 的键值对，用于替换模板中的 {key} 占位符。

        Returns:
            填充后的提示词字符串。若文件不存在返回空字符串；
            若缺少某占位符的变量，使用原始模板（不填充），并输出 warning。

        Note:
            模板中若需要输出字面花括号 {{ 或 }}，需写成双花括号进行转义。
            这是因为底层使用 str.format()，双重花括号会被处理为单个花括号。
        """
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
        """清空模板缓存，下次加载时会重新从磁盘读取。"""
        cls._cache.clear()
