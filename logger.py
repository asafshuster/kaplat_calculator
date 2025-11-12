import os
import logging
from logging import Logger
from datetime import datetime
from typing import Optional

# Ensure the 'logs' directory exists
os.makedirs("logs", exist_ok=True)

class RequestFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = datetime.fromtimestamp(record.created)
        return ct.strftime("%d-%m-%Y %H:%M:%S.") + f"{int(record.msecs):03d}"

    def format(self, record):
        record.asctime = self.formatTime(record)
        base = f"{record.asctime} {record.levelname}: {record.getMessage()}"
        if hasattr(record, "request_number"):
            base += f" | request #{record.request_number}"
        return base

def setup_logger(name: str, log_file: str, level: int = logging.INFO, to_stdout: bool = False) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Avoid duplicate logs

    # Avoid adding handlers multiple times (important for reloads)
    if logger.handlers:
        return logger

    formatter = RequestFormatter()

    # File handler
    file_handler = logging.FileHandler(f"logs/{log_file}", mode="a")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Optional stdout handler
    if to_stdout:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger

def get_logger_level(name: str) -> Optional[str]:
    logger = logging.getLogger(name)
    if logger and logger.level:
        return logging.getLevelName(logger.level)
    return None

def set_logger_level(name: str, level_name: str) -> bool:
    logger = logging.getLogger(name)
    level = getattr(logging, level_name.upper(), None)
    if not isinstance(level, int):
        return False
    logger.setLevel(level)
    return True


# # pre-setup the logger here
request_logger = setup_logger("request-logger", "requests.log", level=logging.INFO, to_stdout=True)
stack_logger = setup_logger("stack-logger", "stack.log", level=logging.INFO)
independent_logger = setup_logger("independent-logger", "independent.log", level=logging.DEBUG)

