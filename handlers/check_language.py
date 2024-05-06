import os
import shutil
from io import BytesIO

import re
import cv2
import fitz
from langdetect import detect
from ppocronnx.predict_system import TextSystem
from logger import logger
from save_filesys_db import save_Language

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor

IMAGE_PATH = './assets/images'
LANGUAGES = ['EN', 'FR', 'NL', 'DE', 'JA', 'ZH', 'ES', 'AR', 'PT']
CODE_SUCCESS = 0
CODE_ERROR = 1


# 判断单页文本是否为语言目录页。
def find_language_index_page(page_texts):
    # 正则表达式用于匹配字符串末尾的页码
    page_number_pattern = re.compile(r"(\s\d+|\d+)$")
    language_entries_count = 0
    current_pagenum = 0
    directory_information = {}
    is_index = 0

    for i in range(len(page_texts)):
        # 只检查每个元素的前两个字符
        if any(page_texts[i][:2] == lang for lang in LANGUAGES):
            # 检查当前元素是否以页码结束
            language = page_texts[i][:2]
            match = page_number_pattern.search(page_texts[i])
            if match:
                page_number = match.group()
                if (int(page_number) > current_pagenum):
                    language_entries_count += 1
                    current_pagenum = int(page_number)
                    directory_information[language] = int(page_number)
            # 否则，检查下一个元素是否包含页码
            elif i + 1 < len(page_texts):
                next_match = page_number_pattern.match(page_texts[i + 1])
                if next_match:
                    next_page_number = next_match.group()
                    if (int(next_page_number) > current_pagenum):
                        language_entries_count += 1
                        i += 1  # 跳过下一个元素，因为它是页码
                        current_pagenum = int(next_page_number)
                        directory_information[language] = int(next_page_number)

    # 如果一个页面上有超过两个匹配项，则认为是语言目录页
    is_index = language_entries_count > 2

    return is_index, directory_information


# 使用OCR技术读取图像中的文本，确定语言目录页。
def get_image_text(extracted_images):
    text_sys = TextSystem()
    language_index_pages = []  # 存储识别为语言目录的页面编号
    directory_information = {}
    has_match_index = False

    # 检测并识别文本
    for index, image_path in enumerate(extracted_images):
        if has_match_index:
            break

        print(f"Processing page: {index + 1}")  # 打印当前处理的PDF页号
        img = cv2.imread(image_path)
        res = text_sys.detect_and_ocr(img)
        # 仅获取识别的文本内容
        page_texts = [boxed_result.ocr_text for boxed_result in res]

        # 判断当前页面是否为语言目录页
        is_index, directory = find_language_index_page(page_texts)
        logger.info(is_index, directory)
        if is_index:
            language_index_pages.append(index + 1)  # 页号是从1开始的
            directory_information = directory
            has_match_index = True
    logger.info(f"directory_information: {directory_information}")

    return language_index_pages, directory_information


# pdf转图像
def convert_pdf_to_images(doc, limit):
    extracted_images = []

    # 确保文件夹存在
    if not os.path.exists(IMAGE_PATH):
        os.makedirs(IMAGE_PATH)

    for page_num in range(len(doc)):
        if page_num > limit - 1:
            break
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        output_image_path = os.path.join(
            IMAGE_PATH, f"output_page_{page_num}.png")
        pix.save(output_image_path)
        extracted_images.append(output_image_path)

    return extracted_images


# 提取目录
def get_directory(doc, limit):
    # 将PDF页面转换为图像
    extracted_images = convert_pdf_to_images(doc, limit)

    # 从图像中识别文本
    language_index_pages, directory_information = get_image_text(
        extracted_images)
    print(f"language_index_pages: {language_index_pages}")

    return language_index_pages, directory_information

# 从一个文档中按照不同语言的页码范围提取文本，并将这些文本按语言分类存储在一个字典中。
def extract_text_by_language(doc, language_pages):
    # 初始化一个字典，用来存储每种语言的文本
    language_texts = {}

    # 总页数
    total_pages = doc.page_count

    # 按语言的起始页码排序
    sorted_languages = sorted(language_pages.items(), key=lambda item: item[1])

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
            detected_language = detect(text)
            detected_languages[language_code] = detected_language
        except Exception as e:
            detected_languages[language_code] = f"Error: {str(e)}"

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


def find_mismatched_languages(doc, detected_languages, page_number):
    mismatched = {}

    # 遍历 detected_languages 字典
    for key, value in detected_languages.items():
        # 比较键（key）和值（value）是否相同，忽略大小写，如果不匹配则添加到 mismatched 字典中
        if key.lower() != value.lower():
            mismatched[key] = value

    return mismatched


# 主函数
def check_language(username, file, filename, limit):
    logger.info("---begin check_language---")
    logger.info(f"username : {username}")
    logger.info(f"limit : {limit}")
    doc = fitz.open(stream=BytesIO(file))
    # doc = fitz.open(file)
    total_pages = doc.page_count
    if limit == -1:
        limit = 15
    language_pages = get_directory(doc, limit)
    if not language_pages[0]:
        msg = "请仔细检查，该文件无语言目录"
        logger.info(msg)
        save_Language(username, doc, filename, CODE_ERROR, None, [], msg)
        return CODE_ERROR, {}, msg
    language_message = language_pages[1]
    texts_by_languages = extract_text_by_language(doc, language_pages[1])
    detected_languages = detect_language_of_texts(texts_by_languages)

    mismatched_languages = find_mismatched_languages(
        doc, detected_languages, language_pages[0])
    # Printing the new dictionary with mismatched languages
    logger.info(f"detected_languages: {detected_languages}")
    logger.info(f"mismatched_languages: {mismatched_languages}")
    language = generate_language_report(
        mismatched_languages, language_message, total_pages)

    shutil.rmtree(IMAGE_PATH)
    data = {
        # Assuming language_page is a variable holding some data
        'language_page': language_pages[0][0],
        'language': language  # A success message
    }
    logger.info("save file")
    save_Language(username, doc, filename, CODE_SUCCESS,
                  language_pages[0][0], language, None)
    logger.info("save success")
    doc.close()
    logger.info("---end check_language---")
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
    def process_async(self, username, file, filename, limit):
        return check_language(username, file, filename, limit)
    async def post(self):
        username = self.current_user
        limit = int(self.get_argument('limit'))
        files = self.get_files()
        file = files[0]
        body = file["body"]
        filename = file["filename"]
        code, data, msg = await self.process_async(
            username, body, filename, limit)

        custom_data = {
            'code': code,
            'data': data,
            'msg': msg
        }

        self.write(custom_data)
