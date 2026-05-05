import json
from pathlib import Path
from .path_utils import PathUtils


class FileUtils:
    """File I/O: JSON load/save, text read, existence check."""

    @staticmethod
    def load_json(relative_path: str) -> dict:
        path = PathUtils.get_abs_path(relative_path)
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_json(relative_path: str, data: dict) -> None:
        path = PathUtils.get_abs_path(relative_path)
        PathUtils.ensure_dir(path.parent)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def read_text(relative_path: str) -> str:
        path = PathUtils.get_abs_path(relative_path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def file_exists(relative_path: str) -> bool:
        return PathUtils.get_abs_path(relative_path).exists()
