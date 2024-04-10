import logging
from logging.handlers import RotatingFileHandler
import os

# 创建 logs 目录
if not os.path.exists('logs'):
    os.mkdir('logs')

# 配置日志器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建一个 handler，用于写入日志文件
file_handler = RotatingFileHandler('logs/my_app.log', maxBytes=10240, backupCount=10)

# 创建一个 handler，用于将日志输出到控制台
stream_handler = logging.StreamHandler()

# 设置日志格式，移除了记录器的名称（%(name)s）和毫秒（,%f）
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 应用日志格式
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# 添加 handler 到 logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)
