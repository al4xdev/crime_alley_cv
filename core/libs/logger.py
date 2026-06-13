from __future__ import annotations
from typing import TYPE_CHECKING
import logging
from pathlib import Path

def _log_method(func):
    def wrapper(self, msg: str, *args, **kwargs):
        if self._logger:
            self._count += 1
            msg = f"[{self._count}] {msg}"
        return func(self, msg, *args, **kwargs)
    return wrapper

class Log:
    def __init__(self):
        if TYPE_CHECKING:
            self._logger: logging.Logger | None
            self._count: int

    @classmethod
    def config(cls, log_file: Path, tool: str = "core") -> Log:
        instance = cls()
        instance._count = 0
        
        logger = logging.getLogger(tool)
        logger.setLevel(logging.INFO)
        
        if logger.handlers:
            logger.handlers.clear()
            
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s): %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        instance._logger = logger
        return instance

    @_log_method
    def info(self, msg: str) -> Log:
        if self._logger:
            self._logger.info(msg)
        return self

    @_log_method
    def warning(self, msg: str) -> Log:
        if self._logger:
            self._logger.warning(msg)
        return self

    @_log_method
    def error(self, msg: str) -> Log:
        if self._logger:
            self._logger.error(msg)
        return self

    @_log_method
    def debug(self, msg: str) -> Log:
        if self._logger:
            self._logger.debug(msg)
        return self
