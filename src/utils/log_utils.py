# 日志工具模块 —— 控制台 + 文件双通道日志，支持 DEBUG/INFO/WARNING/ERROR 级别。
import logging
import sys
from pathlib import Path


class LogUtils:
    """Custom logger with console + file output, supporting DEBUG/INFO/WARNING/ERROR levels."""

    # 单例 Logger 实例，整个应用共享同一个 logger。
    _logger: logging.Logger | None = None

    @classmethod
    def setup(cls, log_dir: str = "logs", log_file: str = "app.log", level: str = "DEBUG") -> logging.Logger:
        """初始化日志系统：创建控制台 handler（INFO 级别）和文件 handler（DEBUG 级别）。

        Args:
            log_dir: 日志文件存放目录，默认为 logs/。
            log_file: 日志文件名，默认为 app.log。
            level: 日志级别，默认为 DEBUG。

        Returns:
            配置完成的 logging.Logger 实例（单例，仅首次调用时创建）。
        """
        # 单例检查：已有实例则直接返回，避免重复创建 handler 导致日志重复输出。
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
        """获取 Logger 实例，若未初始化则自动调用 setup() 进行默认初始化。"""
        if cls._logger is None:
            cls.setup()
        return cls._logger

    # 以下为便捷方法，对应标准 logging 的四个级别，无需手动调用 _get()。
    @classmethod
    def debug(cls, msg: str) -> None: cls._get().debug(msg)
    @classmethod
    def info(cls, msg: str) -> None: cls._get().info(msg)
    @classmethod
    def warning(cls, msg: str) -> None: cls._get().warning(msg)
    @classmethod
    def error(cls, msg: str) -> None: cls._get().error(msg)
