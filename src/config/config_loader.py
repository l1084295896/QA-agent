import os
import re
from pathlib import Path
import yaml
from dotenv import load_dotenv

from ..utils.log_utils import LogUtils


class ConfigLoader:
    """Load YAML configs with ${ENV_VAR} substitution. Caches loaded configs."""

    def __init__(self, config_dir: str = "config"):
        load_dotenv()
        self.config_dir = Path(config_dir)
        self._cache: dict[str, dict] = {}

    def _resolve_env_vars(self, value):
        if isinstance(value, str):
            def replace_match(m):
                var_name = m.group(1)
                return os.environ.get(var_name, "")
            return re.sub(r'\$\{([^}]+)\}', replace_match, value)
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(v) for v in value]
        return value

    def load(self, name: str) -> dict:
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
        config = self.load(config_name)
        for key in keys:
            if isinstance(config, dict):
                config = config.get(key, {})
            else:
                return {}
        return config
