import os
import shutil
from io import BytesIO

import re
import cv2
import fitz
from langdetect import detect
from ppocronnx.predict_system import TextSystem
from save_filesys_db import save_Language

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
        print(is_index, directory)
        if is_index:
            language_index_pages.append(index + 1)  # 页号是从1开始的
            directory_information = directory
            has_match_index = True

    print(f"directory_information: {directory_information}")

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


def extract_text_by_language(doc, language_pages):
    # Initialize the dictionary to hold the text for each language
    language_texts = {}

    # Get the total number of pages in the document
    total_pages = doc.page_count

    # Sort the languages by the starting page number
    sorted_languages = sorted(language_pages.items(), key=lambda item: item[1])

    # Go through each language and its start page
    for i, (language, start_page) in enumerate(sorted_languages):
        # Determine the end page
        # If it's not the last language, the end page is the start page of the next language - 1
        # If it's the last language, the end page is the last page of the document
        end_page = sorted_languages[i + 1][1] - 1 if i + \
            1 < len(sorted_languages) else total_pages

        # Extract text from the specified page range
        text = ""
        for page_num in range(start_page, end_page + 1):
            # Page numbers are zero-indexed in PyMuPDF
            page_text = doc[page_num - 1].get_text()
            text += page_text

        # Add the extracted text to the dictionary
        language_texts[language] = text

    return language_texts


def detect_language_of_texts(texts_by_languages):
    detected_languages = {}

    for language_code, text in texts_by_languages.items():
        try:
            # Detect the language of the text
            detected_language = detect(text)
            detected_languages[language_code] = detected_language
        except Exception as e:
            # If language detection fails, print an error message
            detected_languages[language_code] = f"Error: {str(e)}"

    return detected_languages


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

    # Iterate over the detected_languages dictionary
    for key, value in detected_languages.items():
        # Compare the key and value ignoring case, add to mismatched if they don't match
        if key.lower() != value.lower():
            mismatched[key] = value

    return mismatched


# 主函数
def check_language(username, file, filename, limit):
    doc = fitz.open(stream=BytesIO(file))
    # doc = fitz.open(file)
    total_pages = doc.page_count
    language_pages = get_directory(doc, limit)
    if not language_pages[0]:
        code = "请仔细检查，该文件无语言目录"
        print(code)
        save_Language(doc, filename, CODE_ERROR, None, [], code)
        return CODE_ERROR, {}, code
    language_message = language_pages[1]
    texts_by_languages = extract_text_by_language(doc, language_pages[1])
    detected_languages = detect_language_of_texts(texts_by_languages)

    mismatched_languages = find_mismatched_languages(
        doc, detected_languages, language_pages[0])
    is_error = False if len(mismatched_languages.keys()) == 0 else True

    # Printing the new dictionary with mismatched languages
    print(f"detected_languages: {detected_languages}")
    print(f"mismatched_languages: {mismatched_languages}")

    language = generate_language_report(
        mismatched_languages, language_message, total_pages)

    shutil.rmtree(IMAGE_PATH)
    data = {
        # Assuming language_page is a variable holding some data
        'language_page': language_pages[0][0],
        'language': language  # A success message
    }
    save_Language(username, doc, filename, CODE_SUCCESS,
                  language_pages[0][0], language, None)
    doc.close()
    return CODE_SUCCESS, data, None

# 测试
# def pdf_to_bytes(file_path):
#     with open(file_path, 'rb') as file:
#         bytes_content = file.read()
#     return bytes_content
# file1 = 'page_number/lang.pdf'  # 请根据实际情况修改路径
# file1 = pdf_to_bytes(file1)
# check_language(file1)
