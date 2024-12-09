from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor
import datetime
import sys

sys.path.append("..")

CODE_SUCCESS = 0
CODE_ERROR = 1
from utils import add_url

from config import RECORD_FILE_ROOT, IMAGE_ROOT, FLIES_ROOT, FRONT
from model import record_count
import os
from datetime import datetime
def save_record_to_txt(record, filename=None):
    """
    将嵌套字典转换为指定的文字格式，并保存到指定目录下以时间戳命名的文本文件中。

    :param record: dict，嵌套字典，格式如用户ID -> 功能 -> {'record_count': int, 'datetime': list}
    :param filename: str，可选，输出的文本文件名。如果未提供，将使用时间戳自动生成文件名。
    """
    # 确保 RECORD_FILE_ROOT 目录存在，如果不存在则创建
    if not os.path.exists(RECORD_FILE_ROOT):
        try:
            os.makedirs(RECORD_FILE_ROOT)
            print(f"目录已创建: {RECORD_FILE_ROOT}")
        except Exception as e:
            print(f"创建目录时出错: {e}")
            return

    # 如果未提供 filename，生成基于当前时间的时间戳文件名
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        filename = f"{timestamp}.txt"

    # 构建完整的文件路径
    file_path = os.path.join(RECORD_FILE_ROOT, filename)
    file_path = os.path.normpath(file_path).replace('\\', '/')  # 确保路径为Linux风格

    lines = []
    for user_id, features in record.items():
        # 开始构建每一行的文本
        line = f"用户{user_id}"
        feature_texts = []
        for feature_name, details in features.items():
            record_count = details.get('record_count', 0)
            datetime_list = details.get('datetime', [])
            feature_text = f"使用功能 {feature_name} {record_count}次，时间为 {datetime_list}"
            feature_texts.append(feature_text)
        # 将所有功能的文本用逗号连接
        line += "，" + "，".join(feature_texts)
        lines.append(line)

    # 将所有用户的行用换行符连接
    final_text = "\n".join(lines)

    # 将文本写入文件，使用UTF-8编码以支持中文字符
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"记录已成功保存到 {file_path} 文件中！")
    except Exception as e:
        print(f"保存文件时出错: {e}")
    return file_path

def select_record():
    record = record_count.get_user_record()
    file_path = save_record_to_txt(record)
    url = add_url(file_path)
    print(f"url:{url}")
    return url


class SelectRecordHandler(MainHandler):
    @run_on_executor
    def process_async(self):
        return select_record()

    async def post(self):
        url = await self.process_async()
        custom_data = {
            "code": 0,
            "data": url,
            "msg": ''
        }
        self.write(custom_data)









