# 路径工具模块 —— 统一管理项目根目录，所有相对路径均基于项目根解析。
from pathlib import Path


class PathUtils:
    """Centralized path resolution — all paths relative to project root."""

    # 项目根目录缓存，首次访问时自动检测。
    _project_root: Path | None = None

    @classmethod
    def set_project_root(cls, path: str | Path) -> None:
        """显式设置项目根目录，覆盖自动检测。"""
        cls._project_root = Path(path).resolve()

    @classmethod
    def get_project_root(cls) -> Path:
        """获取项目根目录路径。

        若未显式设置，则自动推导为当前文件向上三级目录（src/utils -> 项目根）。

        Returns:
            项目根目录的绝对路径。
        """
        if cls._project_root is None:
            cls._project_root = Path(__file__).resolve().parent.parent.parent
        return cls._project_root

    @classmethod
    def get_abs_path(cls, relative_path: str) -> Path:
        """将相对路径转换为基于项目根的绝对路径。"""
        return cls.get_project_root() / relative_path

    @classmethod
    def ensure_dir(cls, path: str | Path) -> None:
        """确保目录存在，若不存在则递归创建。"""
        Path(path).mkdir(parents=True, exist_ok=True)
