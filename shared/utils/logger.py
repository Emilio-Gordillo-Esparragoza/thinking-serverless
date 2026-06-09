import json
import logging
import os
from typing import Any


_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(_LOG_LEVEL)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(_LOG_LEVEL)
        logger.addHandler(handler)

    return logger


def log_struct(logger: logging.Logger, level: int, message: str, **kwargs: Any) -> None:
    record = {"message": message}
    record.update(kwargs)
    logger.log(level, json.dumps(record, default=str))
