import os
from io import BytesIO
import fitz
# from logger import logger
import re
import easyocr
import cv2
import numpy as np
import easyocr  # 导入EasyOCR

from ppocronnx.predict_system import TextSystem
from save_filesys_db import save_Screw

CODE_SUCCESS = 0
CODE_ERROR = 1

# ocr识别螺丝包
def group_text_by_lines(image_bytes, y_tolerance=10):
    """
    将文本按行分组。
    `image_bytes` 是图片的字节流。
    `y_tolerance` 是y坐标的容忍度，用于确定两个文本是否属于同一行。
    """
    # 创建reader对象，指定使用的语言
    reader = easyocr.Reader(['en'], gpu=False)  # 使用gpu=False来强制使用CPU

    # 直接读取图片的字节流
    results = reader.readtext(image_bytes)
    lines = {}
    for (bbox, text, confidence) in results:
        top_left, _, bottom_right, _ = bbox
        # 计算y坐标的中点
        mid_y = (top_left[1] + bottom_right[1]) / 2

        # 检查此文本块应该属于哪一行
        found_line = False
        for key in lines.keys():
            if abs(key - mid_y) <= y_tolerance:
                lines[key].append(text)
                found_line = True
                break
        if not found_line:
            lines[mid_y] = [text]

    # 合并每行的文本，并返回
    grouped_lines = []
    for key in sorted(lines.keys()):
        grouped_lines.append(' '.join(lines[key]))
    return grouped_lines
# 根据获取到的文字组成螺丝包字典
def parse_text_to_dict(lines):
    """
    解析文本行并返回字母与其对应数字的字典。
    `lines` 是一个列表，其中包含至少一个字符串元素。
    第一个元素为字母行，如果存在，第二个元素为含数字的字符串。
    """
    if not lines:
        result = [{'type': 'A', 'count': 0}, {'type': 'A', 'count': 0}, {'type': 'A', 'count': 0},
                  {'type': 'A', 'count': 0}]
        return result

    # 使用正则表达式移除非字母和非空格字符
    clean_letters_line = re.sub(r'[^A-Za-z\s]', '', lines[0])
    # 筛选只包含单一字母的部分
    letters = [letter for letter in clean_letters_line.split() if re.fullmatch(r'[A-Za-z]', letter)]
    numbers = []
    # 如果存在第二行，处理数字
    if len(lines) > 1:
        numbers_with_extra = lines[1].split()
        # 提取数字，如果没有数字则默认为0
        for num in numbers_with_extra:
            digits = ''.join(filter(str.isdigit, num))
            if digits:
                numbers.append(int(digits))
            else:
                numbers.append(0)  # 如果没有数字，添加0
    else:
        # 只有一行时，所有字母对应数字默认为0
        numbers = [0] * len(letters)

    # 创建字母和数字的字典
    result_dict = {letter: num for letter, num in zip(letters, numbers)}

    # 如果数字不足，为剩余字母分配0
    if len(numbers) < len(letters):
        for letter in letters[len(numbers):]:
            result_dict[letter] = 0
    result = [{'type': key, 'count': value} for key, value in result_dict.items()]
    return result
def get_Screw_bags(byte_data):
    lines = group_text_by_lines(byte_data, y_tolerance=10)
    result = parse_text_to_dict(lines)
    data ={
        'result':result
    }
    return CODE_SUCCESS, data, ''


def extract_text_from_pdf(doc, page_number):
    ocr_system = TextSystem()  # 初始化PPOCR的TextSystem
    text_results = {}
    page = doc.load_page(page_number - 1)  # 加载页面，页码从0开始
    image = page.get_pixmap()  # 将PDF页面转换为图像

    # 将图像数据转换为OpenCV格式
    img = cv2.imdecode(np.frombuffer(image.tobytes(), np.uint8), cv2.IMREAD_COLOR)

    if img is not None:
        results = ocr_system.detect_and_ocr(img)
        texts = ' '.join([boxed_result.ocr_text for boxed_result in results])
        text_results[page_number] = texts
    else:
        texts=''

    return texts
# easyocr
# def extract_text_from_pdf(doc, page_number):
#     reader = easyocr.Reader(['en'])  # 创建一个EasyOCR reader，这里使用英文，可以根据需求添加其他语言
#     text_results = {}
#
#     page = doc.load_page(page_number - 1)  # 加载页面，页码从0开始
#     image = page.get_pixmap()  # 将PDF页面转换为图像
#
#     # 将图像数据转换为OpenCV格式
#     img = cv2.imdecode(np.frombuffer(image.tobytes(), np.uint8), cv2.IMREAD_COLOR)
#
#     if img is not None:
#         # 使用EasyOCR进行文本识别
#         results = reader.readtext(img)
#         # 提取识别的文本内容并合并成一个字符串
#         texts = ' '.join([result[1] for result in results])
#         text_results[page_number] = texts
#     else:
#         texts = ''
#     return texts
# 提取步骤页，需要的步骤螺丝
# 提取步骤页，需要的步骤螺丝
def get_step_screw(doc, pages,result_dict):
    # 提取字典键并去除空格
    keys = [key.strip() for key in result_dict.keys()]

    # 将键转换为字符类用于正则表达式
    key_pattern = '[' + ''.join(keys) + ']'
    # 构建正则表达式，包括所有提取的键
    pattern = fr'(\d+)\s*[xX]\s*({key_pattern})|({key_pattern})\s*[xX]\s*(\d+)'

    letter_counts = {}
    letter_pageNumber = {}
    letter_count = {}

    for page_num in pages:
        page = doc.load_page(page_num - 1)  # Page numbering starts from 0
        # text = page.get_text()
        text = extract_text_from_pdf(doc,page_num)
        # print(text)
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


def check_total_and_step(doc, result_dict,step_page):
    count_mismatch = {}  # 数量不匹配的情况

    letter_counts, letter_count, letter_pageNumber = get_step_screw(doc,step_page,result_dict)

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
            'step_count': letter_count.get(key, None),
            'step_page_no': letter_pageNumber.get(key, None)
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
    doc = fitz.open(stream=BytesIO(file))
    # 获取螺丝包
    result_dict = {item['type']: item['count'] for item in table}
    print("Screw bag:", result_dict)
    step_page = list(range(start, end + 1))
    if start<1 or end>doc.page_count:
        return CODE_ERROR, {}, '请检查步骤页输入是否正确'
    count_mismatch, letter_count, letter_pageNumber, result_dict = check_total_and_step(
        doc, result_dict, step_page)
    mismatch_dict, match_dict = create_dicts(
        result_dict, count_mismatch, letter_count, letter_pageNumber)

    print("Mismatch Dict:", mismatch_dict)
    print("Match Dict:", match_dict)

    data = {
        'mismatch_dict': mismatch_dict,
        'match_dict': match_dict
    }
    print("save file")
    save_Screw(username, doc, filename, CODE_SUCCESS,
                mismatch_dict, match_dict, None)
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
# result = [{'key': 'A', 'value': 17}, {'key': 'B', 'value': 18}, {'key': 'C', 'value': 2}, {'key': 'D', 'value': 4}, {'key': 'E', 'value': 4}]
# start =6
# end =14
# check_screw('username', file1, 'filename', result, start, end)



