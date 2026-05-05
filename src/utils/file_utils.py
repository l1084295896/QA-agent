# 文件工具模块 —— JSON 读写、文本读取、文件存在性检查，基于项目根路径。
import json
from pathlib import Path
from .path_utils import PathUtils


class FileUtils:
    """File I/O: JSON load/save, text read, existence check."""

    @staticmethod
    def load_json(relative_path: str) -> dict:
        """加载 JSON 文件并解析为 dict。

        Args:
            relative_path: 相对于项目根的 JSON 文件路径。

        Returns:
            解析后的字典，文件不存在时返回空字典 {}。
        """
        path = PathUtils.get_abs_path(relative_path)
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_json(relative_path: str, data: dict) -> None:
        """将 dict 写入 JSON 文件（自动创建父目录，ensure_ascii=False 保留中文）。

        Args:
            relative_path: 相对于项目根的目标 JSON 文件路径。
            data: 要保存的字典数据。
        """
        path = PathUtils.get_abs_path(relative_path)
        PathUtils.ensure_dir(path.parent)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def read_text(relative_path: str) -> str:
        """读取文本文件全部内容。

        Args:
            relative_path: 相对于项目根的文本文件路径。

        Returns:
            文件的全部文本内容。
        """
        path = PathUtils.get_abs_path(relative_path)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def file_exists(relative_path: str) -> bool:
        """检查文件是否存在。

        Args:
            relative_path: 相对于项目根的文件路径。

        Returns:
            True 表示文件存在。
        """
        return PathUtils.get_abs_path(relative_path).exists()
