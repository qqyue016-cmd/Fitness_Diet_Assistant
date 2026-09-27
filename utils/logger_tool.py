'''
日志处理工具
'''
import os
import logging
from datetime import datetime
from utils.path_tool import get_abs_path

# 日志保存目录
LOG_ROOT = get_abs_path('logs')

# 确保目录存在
os.makedirs(LOG_ROOT, exist_ok=True)

# 规范日志格式
DEFAULT_LOG_FORMAT = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s'
)

def get_logger(
        name:str='Diet_Assistant',
        console_level = logging.INFO,
        file_level = logging.DEBUG,
        log_file = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免生成handler
    if logger.handlers:
        return logger

    # 创建控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(DEFAULT_LOG_FORMAT)

    # 创建日志文件
    if not log_file:
        log_file = os.path.join(LOG_ROOT, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')

    # 创建文件handler
    file_handler = logging.FileHandler(log_file,mode='a',encoding='utf-8')
    file_handler.setLevel(file_level)
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = get_logger()

if __name__ == '__main__':
    logger.info('this is a info message')