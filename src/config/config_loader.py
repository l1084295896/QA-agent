# 配置加载模块 —— 加载 YAML 配置文件，支持 ${ENV_VAR} 环境变量替换，带缓存。
import os
import re
from pathlib import Path
import yaml
from dotenv import load_dotenv

from ..utils.log_utils import LogUtils


class ConfigLoader:
    """Load YAML configs with ${ENV_VAR} substitution. Caches loaded configs."""

    def __init__(self, config_dir: str = "config"):
        # 加载 .env 文件中的环境变量，使其可通过 os.environ 访问。
        load_dotenv()
        self.config_dir = Path(config_dir)
        # 配置缓存：key 为配置名（不含 .yml），value 为解析后的配置 dict。
        self._cache: dict[str, dict] = {}

    def _resolve_env_vars(self, value):
        """递归替换值中的所有 ${ENV_VAR} 占位符为对应的环境变量值。

        支持三种类型：
        - 字符串：使用正则 r'\\$\\{([^}]+)\\}' 匹配 ${VAR_NAME} 并从 os.environ 获取值。
        - 字典：递归处理每个 value。
        - 列表：递归处理每个元素。
        - 其他类型（int、bool 等）：原样返回。

        Args:
            value: 待解析的值，可以是任意 YAML 支持的类型。

        Returns:
            替换环境变量后的值。
        """
        if isinstance(value, str):
            def replace_match(m):
                var_name = m.group(1)
                return os.environ.get(var_name, "")
            # 正则 \\$\\{([^}]+)\\} 匹配 ${SOME_VAR} 格式的占位符。
            return re.sub(r'\$\{([^}]+)\}', replace_match, value)
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(v) for v in value]
        return value

    def load(self, name: str) -> dict:
        """加载指定名称的 YAML 配置文件（自动解析环境变量，结果会缓存）。

        Args:
            name: 配置文件名（不含 .yml 扩展名）。

        Returns:
            解析后的配置字典。

        Raises:
            FileNotFoundError: 配置文件不存在时抛出。
        """
        if name in self._cache:
            return self._cache[name]

        file_path = self.config_dir / f"{name}.yml"
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        config = self._resolve_env_vars(config)
        self._cache[name] = config
        LogUtils.debug(f"Loaded config: {name}")
        return config

    def get(self, config_name: str, *keys: str):
        """按层级键路径获取配置值。

        Args:
            config_name: 配置文件名（不含 .yml）。
            *keys: 逐层访问的键名，例如 get("models", "text_model", "temperature")
                   会依次访问 config["text_model"]["temperature"]。

        Returns:
            最终命中的配置值；若中间某层不是 dict，则返回空字典 {}。
        """
        config = self.load(config_name)
        for key in keys:
            if isinstance(config, dict):
                config = config.get(key, {})
            else:
                return {}
        return config
