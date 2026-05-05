from pathlib import Path


class PathUtils:
    """Centralized path resolution — all paths relative to project root."""

    _project_root: Path | None = None

    @classmethod
    def set_project_root(cls, path: str | Path) -> None:
        cls._project_root = Path(path).resolve()

    @classmethod
    def get_project_root(cls) -> Path:
        if cls._project_root is None:
            cls._project_root = Path(__file__).resolve().parent.parent.parent
        return cls._project_root

    @classmethod
    def get_abs_path(cls, relative_path: str) -> Path:
        return cls.get_project_root() / relative_path

    @classmethod
    def ensure_dir(cls, path: str | Path) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)
