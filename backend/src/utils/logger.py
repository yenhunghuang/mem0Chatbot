"""
日誌記錄模組：提供統一的日誌管理

此模組設定應用程式日誌，包括檔案輪換、格式化和日誌級別控制。
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from ..config import settings


def get_logger(name: str) -> logging.Logger:
    """
    取得或建立命名的記錄器

    Args:
        name: 記錄器名稱（通常為 __name__）

    Returns:
        logging.Logger: 設定好的記錄器實例
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)

    # 避免重複的 handlers
    if logger.hasHandlers():
        return logger

    # 建立日誌目錄
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 設定格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 檔案 handler（帶輪換）
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setLevel(settings.log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
