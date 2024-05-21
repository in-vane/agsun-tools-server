import os
import pdfplumber
from io import BytesIO
import time
import re
import fitz
from langdetect import detect
from logger import logger
import copy
from save_filesys_db import save_Language

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor


LANGUAGES = [
    'EN', 'FR', 'NL', 'DE', 'JA', 'ZH', 'ES', 'AR', 'PT', 'RU',
    'IT', 'KO', 'SV', 'PL', 'TR', 'HE', 'TH', 'CS', 'DA', 'FI',
    'NO', 'HU', 'ID', 'MS', 'VI', 'EL', 'SK', 'SL', 'BG', 'UK',
    'HR', 'SI', 'DK', 'CZ'
]
CODE_SUCCESS = 0
CODE_ERROR = 1
# 获取目录
def extract_language_message(line):
    # 创建正则表达式，检测语言缩写和至少一个数字，可能有范围
    pattern = rf"\b({'|'.join(LANGUAGES)})\b.*?(\d+)(?:-\d+)?"

    # 判断给定的行是否包含语言缩写和数字
    match = re.search(pattern, line)
    if match:
        language = match.group(1)  # 语言缩写
        start_page = int(match.group(2))  # 起始页码
        dict = {language: start_page}
        return dict

    return None

def extract_language(pdf_path, num):
    language_message = {}  # 初始化一个空字典来存储所有语言信息
    # 打开 PDF 文件
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[num - 1]  # 页面索引从0开始，因此第三页是索引2
        text = page.extract_text()
        # 如果第三页有文本，按行打印
        if text:
            for line in text.split('\n'):
                result = extract_language_message(line)
                if result:
                    language_message.update(result)  # 更新字典
        else:
            language_message = {}
    if len(language_message) == 0:
        language_message = {'DE': 0, 'EN': 0, 'NL': 0}
        # 如果没有找到任何语言信息，使用OCR扫描页面
    result_list = []
    for type_key, count_value in language_message.items():
        result_list.append({
            'key': time.time(),  # 获取当前时间戳
            'language': type_key,  # 语言代码
            'start': count_value  # 对应的页码
        })
    result_list = sorted(result_list, key=lambda x: x['start'])
    first_start = result_list[0]['start']
    return result_list, first_start

def get_language_directory(pdf_path, num):
    result, first_start  = extract_language(pdf_path, num)
    print(f"识别到的语音目录{result}")
    data = {
        'result': result,
        'start': first_start
    }
    return CODE_SUCCESS, data, ''


def convert_list_to_dict(items_list):
    result_dict = {}
    for item in items_list:
        # 将每个条目的'language'作为键，'start'作为值
        result_dict[item['language']] = item['start']
    return result_dict
# 从一个文档中按照不同语言的页码范围提取文本，并将这些文本按语言分类存储在一个字典中。
def extract_text_by_language(doc, language_message, start):
    # 找出字典中的最小值
    min_value = min(language_message.values())
    adjustment = start - min_value
    print(adjustment)
    # 更新字典
    for key in language_message:
        language_message[key] += adjustment
    # 初始化一个字典，用来存储每种语言的文本
    language_texts = {}

    # 总页数
    total_pages = doc.page_count
    print(language_message)
    # 按语言的起始页码排序
    sorted_languages = sorted(language_message.items(), key=lambda item: item[1])

    # 遍历每种语言及其起始页
    for i, (language, start_page) in enumerate(sorted_languages):
        # 确定结束页码
        # 如果不是最后一种语言，则结束页是下一种语言的起始页减1
        # 如果是最后一种语言，则结束页是文档的最后一页
        end_page = sorted_languages[i + 1][1] - 1 if i + \
            1 < len(sorted_languages) else total_pages

        # 从指定的页码范围提取文本
        text = ""
        for page_num in range(start_page, end_page + 1):
            # 在PyMuPDF中，页码是从零开始索引的
            page_text = doc[page_num - 1].get_text()
            text += page_text

        # 将提取的文本添加到字典中
        language_texts[language] = text

    return language_texts

# 检测并确认文本中的语言。它接收一个包含多种语言文本的字典，然后使用一个语言检测工具langdetect确定每一段文本的语言
def detect_language_of_texts(texts_by_languages):
    detected_languages = {}

    for language_code, text in texts_by_languages.items():
        try:
            detected_language = detect(text).upper()
            detected_languages[language_code] = detected_language
        except Exception as e:
            detected_languages[language_code] = f"Error: {str(e)}"
    print(detected_languages)
    return detected_languages

# 生成一份关于文档中语言标记和实际检测语言是否匹配的详细报告。其目的是辅助用户了解在文档的不同页码范围内，
# 每种指定的语言是否与实际检测到的语言相符。
def generate_language_report(mismatched_languages, language_message, total_pages):
    # 使用字典推导式将每个值转换为大写
    mismatched_languages = {key: value.upper()
                            for key, value in mismatched_languages.items()}

    # 计算每种语言的页码范围
    sorted_languages = sorted(language_message.items(), key=lambda x: x[1])
    language_ranges = {}
    for i, (lang, start_page) in enumerate(sorted_languages):
        end_page = total_pages if i == len(
            sorted_languages) - 1 else sorted_languages[i + 1][1] - 1
        language_ranges[lang] = [start_page, end_page]

    # 生成不匹配语言的详细信息
    result = []
    for lang, actual_lang in mismatched_languages.items():
        if lang in language_ranges:
            error_entry = {
                'language': lang,
                'page_number': language_ranges[lang],
                'error': True,
                'actual_language': actual_lang
            }
            result.append(error_entry)
            # 删除不匹配的语言，以便后续添加剩余正确的语言信息
            del language_message[lang]

    # 添加剩余正确的语言信息
    for lang in language_message.keys():
        if lang in language_ranges:
            correct_entry = {
                'language': lang,
                'page_number': language_ranges[lang],
                'error': False,  # 正确的语言标记为无错误
                'actual_language': lang  # 实际语言与标记语言相同
            }
            result.append(correct_entry)

    return result


def find_mismatched_languages(detected_languages):
    # 创建等价的语言代码映射
    equivalent_languages = {
        'cz': 'cs',
        'cs': 'cz',
        'dk': 'da',
        'da': 'dk'
    }

    mismatched = {}

    # 遍历 detected_languages 字典
    for key, value in detected_languages.items():
        # 将键和值都转为小写，便于比较
        key_lower = key.lower()
        value_lower = value.lower()

        # 检查是否匹配，包括等价语言的处理
        if key_lower != value_lower:
            # 检查是否是特定的等价语言
            if key_lower in equivalent_languages:
                # 如果它们是互相等价的
                if equivalent_languages[key_lower] != value_lower:
                    mismatched[key] = value
            else:
                mismatched[key] = value

    return mismatched


# 主函数
def check_language(username, file, filename, language_message, page):
    print("---begin check_language---")
    print(f"username : {username}")
    doc = fitz.open(file)
    language_new_message = {}
    for item in language_message:
        language = item['language']
        start = item['start']
        language_new_message[language] = start
    for key in language_new_message:
        language_new_message[key] = int(language_new_message[key])
    print(f"语音目录为:{language_new_message}")
    total_pages = doc.page_count
    language_info = copy.deepcopy(language_message)
    texts_by_languages = extract_text_by_language(doc, language_new_message, page)
    detected_languages = detect_language_of_texts(texts_by_languages)

    mismatched_languages = find_mismatched_languages(
         detected_languages)
    # Printing the new dictionary with mismatched languages
    print(f"detected_languages: {detected_languages}")
    print(f"mismatched_languages: {mismatched_languages}")
    language = generate_language_report(
        mismatched_languages, language_new_message, total_pages)

    data = {
        'language': language  # A success message
    }
    print("save file")
    # save_Language(username, doc, filename, CODE_SUCCESS,
    #               language_pages[0][0], language, None)
    print("save success")
    doc.close()
    print("---end check_language---")
    return CODE_SUCCESS, data, None
# 测试
# def pdf_to_bytes(file_path):
#     with open(file_path, 'rb') as file:
#         bytes_content = file.read()
#     return bytes_content
# file1 = 'page_number/lang.pdf'  # 请根据实际情况修改路径
# file1 = pdf_to_bytes(file1)
# check_language(file1)
class LanguageHandler(MainHandler):
    @run_on_executor
    def process_async1(self, file, num):
        return get_language_directory(file, num)

    @run_on_executor
    def process_async2(self, username, file, filename, language_message, start):
        return check_language(username, file, filename, language_message, start)
    async def post(self):
        if self.request.path == "/api/language/context":
            params = tornado.escape.json_decode(self.request.body)
            file = params['file_path']
            num = params['page']
            code, data, msg = await self.process_async1(
                file, num)
        elif self.request.path == "/api/language/compare":
            username = self.current_user
            params = tornado.escape.json_decode(self.request.body)
            file = params['file_path']
            file_name = os.path.basename(file)
            language_message = params['table']
            start = int(params['start'])
            print("文件名:", file_name)
            code, data, msg = await self.process_async2(
                username, file, file_name, language_message, start)
        else:
            code = 1
            data = {}
            msg = '请检查你的网址'
        custom_data = {
            'code': code,
            'data': data,
            'msg': msg
        }

        self.write(custom_data)
