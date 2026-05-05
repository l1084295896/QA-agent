import logging
import sys
from pathlib import Path


class LogUtils:
    """Custom logger with console + file output, supporting DEBUG/INFO/WARNING/ERROR levels."""

    _logger: logging.Logger | None = None

    @classmethod
    def setup(cls, log_dir: str = "logs", log_file: str = "app.log", level: str = "DEBUG") -> logging.Logger:
        if cls._logger is not None:
            return cls._logger

        logger = logging.getLogger("qa_agent")
        logger.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        logger.handlers.clear()

        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        logger.addHandler(console)

        Path(log_dir).mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(Path(log_dir) / log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        ))
        logger.addHandler(file_handler)

        cls._logger = logger
        return logger

    @classmethod
    def _get(cls) -> logging.Logger:
        if cls._logger is None:
            cls.setup()
        return cls._logger

    @classmethod
    def debug(cls, msg: str) -> None: cls._get().debug(msg)
    @classmethod
    def info(cls, msg: str) -> None: cls._get().info(msg)
    @classmethod
    def warning(cls, msg: str) -> None: cls._get().warning(msg)
    @classmethod
    def error(cls, msg: str) -> None: cls._get().error(msg)
