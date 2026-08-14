from pydantic import BaseModel, Field
from typing import Literal
from loguru import logger
from collections import Counter
from functools import wraps
import time 

class LogEntry(BaseModel):
    level: str
    message: str
    timestamp: float = Field(default_factory=time.time)

def count_calls():
    def decorator(func):
        counter = 0
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal counter
            counter += 1
            logger.debug(f"Количество вызовов - {counter}")
            result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

class SafeFileLogger:
    def __init__(self, filepath: str, max_entries: int = 100):
        self._counter = 0
        self._list_log_entry: list[LogEntry] = []
        self.file = None
        self.filepath = filepath
        self.max_entries = max_entries

    def __enter__(self):
        self.file = open(self.filepath, "a")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.file:
            self.file.close()

    def __repr__(self):
        return f"SafeFileLogger(filepath={self.filepath!r}, max_entries={self.max_entries!r})"

    @count_calls()
    def log(self, level: Literal["INFO", "WARNING", "ERROR"], message: str) -> bool:
        if level not in ("INFO", "WARNING", "ERROR"):
            logger.error(f"Недопустимый уровень: {level}")
            return False
        
        if self._counter >= self.max_entries:
            logger.warning(f"Превышен лимит {self.max_entries} : {self._counter}")
            return False
        else:
            log_entry = LogEntry(level=level, message=message)

            self.file.write(f"[{level}] {message}\n")

            self._counter += 1
            self._list_log_entry.append(log_entry)

            logger.debug(f"Запись сделана в {self.filepath}, level - {level} и message - {message}")

            return True

    def get_summary(self):
        level_counts = Counter(entry.level for entry in self._list_log_entry)
        return level_counts

if __name__ == "__main__":
    with SafeFileLogger(filepath="/home/TvoiiSon/Data/Work/IBS/Python/FirstProj/other/test_log.txt", max_entries=3) as save_logger:
        print(save_logger.log("INFO", "first"))
        print(save_logger.log("WARNING", "second"))
        print(save_logger.log("DEBUG", "bad level"))
        print(save_logger.log("ERROR", "third"))
        print(save_logger.log("INFO", "fourth"))
        print(save_logger.get_summary())
