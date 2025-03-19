import logging
from enum import Enum
from abc import ABC, abstractmethod

FILE_PATH = ""
"""Example Usage: C:/Project/Omi/"""

" -------------- ENUMS -------------- "
#region Enums
class FormatterType(Enum):
    SIMPLE = 0
    ADVANCED = 1


class LoggerType(Enum):
    CONSOLE = 0
    FILE = 1
#endregion

" -------------- FORMATTER -------------- "
#region Formatter
class IFormatter(ABC):
    @abstractmethod
    def get_formatter(self) -> logging.Formatter:
        pass


class SimpleFormatter(IFormatter):
    def get_formatter(self) -> logging.Formatter:
        return logging.Formatter('%(asctime)s - %(message)s')


class AdvancedFormatter(IFormatter):
    def get_formatter(self) -> logging.Formatter:
        return logging.Formatter('[%(levelname)s] [%(name)s] [%(asctime)s] => %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class FormatterFactory:
    @staticmethod
    def create_formatter(formatter_type: FormatterType) -> IFormatter:
        formatter_map = {
            FormatterType.SIMPLE: SimpleFormatter,
            FormatterType.ADVANCED: AdvancedFormatter
        }
        formatter_class = formatter_map.get(formatter_type)
        if not formatter_class:
            raise ValueError("Invalid formatter type.")
        return formatter_class()
#endregion

" -------------- LOGGER -------------- "
#region Logger
class ILogger(ABC):
    @abstractmethod
    def log(self, level: int, message: str):
        pass


class BaseLogger(ILogger):
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log(self, level: int, message: str):
        self.logger.log(level, message)


class ConsoleLogger(BaseLogger):
    def __init__(self, name: str, formatter: IFormatter):
        super().__init__(f'ConsoleLogger-{name}')

        handler = logging.StreamHandler()
        handler.setFormatter(formatter.get_formatter())

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)


class FileLogger(BaseLogger):
    def __init__(self, name: str, formatter: IFormatter, file_path: str):
        super().__init__(f'FileLogger-{name}')

        handler = logging.FileHandler(file_path)
        handler.setFormatter(formatter.get_formatter())

        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)


class LoggerFactory:
    @staticmethod
    def create_logger(logger_type: LoggerType, name: str, formatter: FormatterType) -> ILogger:
        if logger_type == LoggerType.CONSOLE:
            return ConsoleLogger(name, formatter)
        elif logger_type == LoggerType.FILE:
            return FileLogger(name, formatter, f"{FILE_PATH}-{name}-Logger.txt")
        else:
            raise ValueError("Invalid logger type.")
#endregion

class Manager:
    def __init__(self, name: str, formatter_type: FormatterType, logger_type: LoggerType):
        formatter = FormatterFactory.create_formatter(formatter_type)
        self.logger = LoggerFactory.create_logger(logger_type, name, formatter)

    def debug(self, message: str) -> None:
        self.logger.log(logging.DEBUG, message)

    def info(self, message: str) -> None:
        self.logger.log(logging.INFO, message)

    def warning(self, message: str) -> None:
        self.logger.log(logging.WARNING, message)

    def error(self, message: str) -> None:
        self.logger.log(logging.ERROR, message)

    def fatal(self, message: str) -> None:
        self.logger.log(logging.FATAL, message)
