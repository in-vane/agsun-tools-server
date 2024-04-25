import os
from io import BytesIO
import fitz
# from logger import logger
import re
import easyocr
import base64
from PIL import Image
import io

import time
import cv2
import numpy as np
import easyocr  # 导入EasyOCR

from ppocronnx.predict_system import TextSystem
from save_filesys_db import save_Screw

CODE_SUCCESS = 0
CODE_ERROR = 1

# ocr识别螺丝包
def extract_Screw_bags(doc, page_number, rect):
    """
    使用PaddleOCR从PDF的指定页面和区域中提取文字。
    :param doc: PyMuPDF的文档对象
    :param page_number: 整数，表示页码（从1开始计数）
    :param rect: 列表或元组，格式为[x, y, w, h]，代表矩形区域，
                 其中x, y是矩形左上角的坐标，w是宽度，h是高度
    :return: 识别的文字
    """
    # 加载指定的页面
    page = doc.load_page(page_number)
    print(page_number)
    print(rect)
    # 从页面中获取指定矩形区域的图像
    clip_rect = fitz.Rect(rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
    pix = page.get_pixmap(clip=clip_rect)

    # 将图像数据转换为OpenCV格式
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    # 如果图像是四通道（RGBA），转换为三通道（BGR），因为PaddleOCR默认处理BGR格式
    if pix.n == 4:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)

    # 创建PaddleOCR TextSystem
    ocr_system = TextSystem()

    # 使用PaddleOCR识别图像中的文字
    results = ocr_system.detect_and_ocr(img_np)

    # 打印results以便理解其结构

    texts = ' '.join([boxed_result.ocr_text for boxed_result in results])
    # 转换所有小写字母为大写
    texts = texts.upper()
    print(texts)
    # 按空格分割文本为单个元素
    elements = texts.split()
    # 初始化结果列表
    result = []
    # 遍历每个元素
    for element in elements:
        # 检查是否为单个大写字母
        if re.fullmatch(r'[A-Z]', element):
            result.append({'key': time.time(),'type': element, 'count': 0})
    index = 0
    # 再次遍历元素，这次寻找包含数字的元素
    for element in elements:
        if re.search(r'\d+', element):
            # 提取第一组数字
            number = int(re.search(r'\d+', element).group())
            # 只有当result中还有未分配的条目时，才分配数字
            if index < len(result):
                result[index]['count'] = number
                index += 1  # 移动到下一个大写字母
    return result


def get_Screw_bags(file, page_number, rect):
    doc = fitz.open(file)
    result = extract_Screw_bags(doc, page_number, rect)
    print(f"识别到的螺丝包{result}")
    data = {
        'result': result
    }
    return CODE_SUCCESS, data, ''


# def extract_text_from_pdf(doc, page_number):
#     ocr_system = TextSystem()  # 初始化PPOCR的TextSystem
#     text_results = {}
#     page = doc.load_page(page_number - 1)  # 加载页面，页码从0开始
#     image = page.get_pixmap()  # 将PDF页面转换为图像
#
#     # 将图像数据转换为OpenCV格式
#     img = cv2.imdecode(np.frombuffer(
#         image.tobytes(), np.uint8), cv2.IMREAD_COLOR)
#
#     if img is not None:
#         results = ocr_system.detect_and_ocr(img)
#         texts = ' '.join([boxed_result.ocr_text for boxed_result in results])
#         text_results[page_number] = texts
#     else:
#         texts = ''
#
#     return texts
# easyocr
def extract_text_from_pdf(doc, page_number):
    reader = easyocr.Reader(['en'])  # 创建一个EasyOCR reader，这里使用英文，可以根据需求添加其他语言
    text_results = {}

    page = doc.load_page(page_number - 1)  # 加载页面，页码从0开始
    image = page.get_pixmap()  # 将PDF页面转换为图像

    # 将图像数据转换为OpenCV格式
    img = cv2.imdecode(np.frombuffer(image.tobytes(), np.uint8), cv2.IMREAD_COLOR)

    if img is not None:
        # 使用EasyOCR进行文本识别
        results = reader.readtext(img)
        # 提取识别的文本内容并合并成一个字符串
        texts = ' '.join([result[1] for result in results])
        text_results[page_number] = texts
    else:
        texts = ''
    return texts
# 提取步骤页，需要的步骤螺丝
# 提取步骤页，需要的步骤螺丝
def replace_special_chars(text):
    # 替换 'z' 或 'Z' 在 'x' 或 'X' 之后或大写字母前的情况
    result = re.sub(r'(?i)(z)(?=(x|[A-Z]))', '2', text)
    result = re.sub(r'(?i)(?<=x)(z)', '2', result)

    # 替换 'i' 在 'x' 或 'X' 之后或大写字母前的情况
    result = re.sub(r'(?i)(i)(?=(x|[A-Z]))', '1', result)
    result = re.sub(r'(?i)(?<=x)(i)', '1', result)

    return result


def get_step_screw(doc, pages, result_dict):
    # 提取字典键并去除空格
    keys = [key.strip() for key in result_dict.keys()]

    # 将键转换为字符类用于正则表达式
    key_pattern = '[' + ''.join(keys) + ']'
    # 构建正则表达式，包括所有提取的键
    pattern = fr'(\d+)\s*[xX*]\s*({key_pattern})|({key_pattern})\s*[xX*]\s*(\d+)'

    letter_counts = {}
    letter_pageNumber = {}
    letter_count = {}

    for page_num in pages:
        page = doc.load_page(page_num - 1)  # Page numbering starts from 0
        text = page.get_text()
        # text = extract_text_from_pdf(doc, page_num)
        matches = re.findall(pattern, text)
        print(f"matches:{matches}matches")
        if len(matches) == 0:
            text = extract_text_from_pdf(doc, page_num)
            print(f"{page_num}可能是图片，开始ocr识别")
            text = replace_special_chars(text)
            print(f"{page_num}:{text}")
            matches = re.findall(pattern, text)
        for match in matches:
            # 通过检查匹配组来确定是哪种模式
            if match[0] and match[1]:  # 数字在前的模式
                count, letter = int(match[0]), match[1]
            elif match[2] and match[3]:  # 字母在前的模式
                letter, count = match[2], int(match[3])
            else:
                continue  # 如果匹配不符合任一模式，则跳过
            # Update letter_counts
            if letter in letter_counts:
                letter_counts[letter] += count
            else:
                letter_counts[letter] = count

            # Update letter_pageNumber
            if letter not in letter_pageNumber:
                letter_pageNumber[letter] = [page_num]
            else:
                # elif page_num not in letter_pageNumber[letter]:
                letter_pageNumber[letter].append(page_num)
            # Update letter_count
            if letter not in letter_count:
                letter_count[letter] = [count]
            else:
                letter_count[letter].append(count)

    print("letter_counts:", letter_counts)
    print("letter_pageNumber:", letter_pageNumber)
    print("letter_count:", letter_count)

    return letter_counts, letter_pageNumber, letter_count


def check_total_and_step(doc, result_dict, step_page):
    count_mismatch = {}  # 数量不匹配的情况

    letter_counts, letter_count, letter_pageNumber = get_step_screw(
        doc, step_page, result_dict)

    # 检查两个字典中的数量是否匹配
    for key in letter_counts:
        if key in result_dict:
            if result_dict[key] != letter_counts[key]:
                count_mismatch[key] = {
                    'expected': result_dict[key], 'actual': letter_counts[key]}
                print(
                    f"数量不匹配: {key}, 应有 {result_dict[key]} 个, 实际有 {letter_counts[key]} 个")
        else:
            print(f"多余的字符: {key} 在 result_dict 中不存在")

    # 检查result_dict是否有letter_counts没有的字符,多余的种类螺丝
    for key in result_dict:
        if key not in letter_counts:
            count_mismatch[key] = {
                'expected': result_dict[key], 'actual': 0}
            print(f"缺少的字符: {key} 在 letter_counts 中不存在")

    return count_mismatch, letter_count, letter_pageNumber, result_dict


def create_dicts(result_dict, count_mismatch, letter_count, letter_pageNumber):
    mismatch_dict = []
    match_dict = []

    for key, value in count_mismatch.items():
        mismatch_dict.append({
            'type': key,
            'total': value['expected'],
            'step_total': value['actual'],
            'step_count': letter_count.get(key, []),
            'step_page_no': letter_pageNumber.get(key, [])
        })
    for key, value in result_dict.items():
        if key not in count_mismatch:
            match_dict.append({
                'type': key,
                'total': value,
                'step_total': value,
                'step_count': letter_count.get(key, []),
                'step_page_no': letter_pageNumber.get(key, [])
            })

    return mismatch_dict, match_dict


# 主函数
def check_screw(username, file, filename, table, start, end):
    print("---begin check_screw---")
    print(f"username : {username}")
    doc = fitz.open(file)
    # 获取螺丝包
    result_dict = {item['type']: item['count'] for item in table}
    print("Screw bag:", result_dict)
    step_page = list(range(start, end + 1))
    if start < 1 or end > doc.page_count:
        return CODE_ERROR, {}, '请检查步骤页输入是否正确'
    count_mismatch, letter_count, letter_pageNumber, result_dict = check_total_and_step(
        doc, result_dict, step_page)
    mismatch_dict, match_dict = create_dicts(
        result_dict, count_mismatch, letter_count, letter_pageNumber)

    print("Mismatch Dict:", mismatch_dict)
    print("Match Dict:", match_dict)
    result = mismatch_dict+match_dict
    data = {
        'result': result
    }
    print("save file")
    # save_Screw(username, doc, filename, CODE_SUCCESS,
    #            mismatch_dict, match_dict, None)
    print("save success")
    doc.close()
    print("---end check_screw---")
    return CODE_SUCCESS, data, None

# 测试
# def pdf_to_bytes(file_path):
#     with open(file_path, 'rb') as file:
#         bytes_content = file.read()
#     return bytes_content

# file1 = '1/AFA/C043544说明书(K114BFI3-AFA-英国30)-A1-YFKL23951.pdf' # 请根据实际情况修改路径
# file1 = '2/ACE.pdf'
# file1 = pdf_to_bytes(file1)
# result = [{’key‘:1,'type': 'A', 'count': 17}]
# , {'key': 'B', 'value': 18}, {'key': 'C', 'value': 2}, {'key': 'D', 'value': 4}, {'key': 'E', 'value': 4}]
# start =6
# end =14
# check_screw('username', file1, 'filename', result, start, end)
