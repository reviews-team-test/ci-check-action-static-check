import logging
from logging.handlers import RotatingFileHandler
from enum import Enum

# 定义一个枚举类来表示日志级别
class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

# 设置日志轮换处理器，最大文件大小为1GB，保留3个备份文件
handler = RotatingFileHandler('dbus_check.log', maxBytes=1*1024*1024*1024, backupCount=3)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# 获取logger实例并添加处理器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# 定义一个装饰器，用于简化日志记录
def log_with_level(level):
    def decorator(func):
        def wrapper(message):
            logger.log(level, message)
            return func(message)
        return wrapper
    return decorator

# 使用装饰器定义不同日志级别的打印函数
@log_with_level(LogLevel.DEBUG.value)
def debug_log(message):
    print(message)

@log_with_level(LogLevel.INFO.value)
def info_log(message):
    print(message)

@log_with_level(LogLevel.WARNING.value)
def warning_log(message):
    print(message)

@log_with_level(LogLevel.ERROR.value)
def error_log(message):
    print(message)

@log_with_level(LogLevel.CRITICAL.value)
def critical_log(message):
    print(message)
