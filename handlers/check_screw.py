import os
from io import BytesIO
import fitz
# from logger import logger
import re

import time
import cv2
import numpy as np
import easyocr  # 导入EasyOCR

from ppocronnx.predict_system import TextSystem
from save_filesys_db import save_Screw

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor

CODE_SUCCESS = 0
CODE_ERROR = 1

def extract_text_from_page(doc, page_number, clip_rect=None):
    """
    使用PyMuPDF从PDF的指定页面提取文字并按位置排序。
    :param doc: PyMuPDF的文档对象
    :param page_number: 整数，表示页码（从1开始计数）
    :param rect: 列表或元组，格式为[x, y, w, h]，代表矩形区域，
                 其中x, y是矩形左上角的坐标，w是宽度，h是高度
    :return: 排序后的该页所有文字及其坐标
    """
    # 加载指定的页面
    page = doc.load_page(page_number)  # 页码从0开始，所以减1
    if clip_rect:
        text_dict = page.get_text("dict", clip=clip_rect)
    else:
        text_dict = page.get_text("dict")
    blocks = text_dict["blocks"]

    # 提取所有文字块
    lines = []
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    lines.append({
                        "text": span["text"],
                        "bbox": span["bbox"]
                    })

    # 按垂直和水平位置排序
    # lines.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    # 按垂直和水平位置排序，忽略小数部分
    lines.sort(key=lambda x: (int(x["bbox"][1]), int(x["bbox"][0])))

    # 组合排序后的文字及其坐标
    # sorted_text = " ".join([line["text"] for line in lines])

    sorted_lines = group_lines_by_y(lines)
    return sorted_lines

def group_lines_by_y(lines):
    """
    按 y 坐标对提取的文字进行分组，并返回按行的 y 坐标排序的集合。
    :param lines: 包含文字及其坐标的字典列表
    :return: 按行的 y 坐标排序的集合，每个元素是属于同一行的文字字符串
    """
    # 定义一个字典用于按行分组
    y_dict = {}

    for line in lines:
        text = line["text"]
        bbox = line["bbox"]
        y_center = (bbox[1] + bbox[3]) / 2  # 计算 y 中心坐标

        # 找到与当前 y 中心坐标接近的键
        found = False
        for key in y_dict.keys():
            if abs(key - y_center) < 5:  # 可以根据需要调整这个阈值
                y_dict[key].append((bbox[0], text))
                found = True
                break

        if not found:
            y_dict[y_center] = [(bbox[0], text)]

    # 对每行的文字按 x 坐标排序，并按 y 坐标排序整个行的集合
    sorted_lines = []
    for y in sorted(y_dict.keys()):
        line_texts = [text for x, text in sorted(y_dict[y])]
        sorted_lines.append(" ".join(line_texts))

    return sorted_lines


def extract_Screw_bags(doc, page_number, rect):
    """
       提取型号及其对应的数量。
       :param text: 包含型号行和数量行的列表
       :return: 型号及其对应数量的列表，每个元素包含时间戳、型号和数量
       """
    print(f"螺丝包页号{page_number+1}")
    print(f"螺丝包区域{rect}")
    clip_rect = fitz.Rect(rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
    text = extract_text_from_page(doc, page_number, clip_rect)
    print(f"文字识别获取到的文字{text}")
    if not text:
        print("文字提取没找到型号行,ocr开始")
        page = doc.load_page(page_number)
        pix = page.get_pixmap(clip=clip_rect)

        # 将图像数据转换为NumPy数组格式
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # 如果图像是四通道（RGBA），转换为三通道（BGR）
        if pix.n == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)

        # 初始化EasyOCR阅读器
        reader = easyocr.Reader(['en'])

        # 使用EasyOCR识别图像中的文字
        results = reader.readtext(img_np)

        # 提取并排序结果
        lines = {}
        for (bbox, text, prob) in results:
            y_center = (bbox[0][1] + bbox[2][1]) / 2
            if y_center not in lines:
                lines[y_center] = []
            lines[y_center].append((bbox[0][0], text))

        # 对每行的文字按 x 坐标排序，并按 y 坐标排序整个行的集合
        sorted_lines = []
        for y in sorted(lines.keys()):
            line_texts = [text for x, text in sorted(lines[y])]
            sorted_lines.append(" ".join(line_texts))

        # 将识别到的所有文字拼接成一个字符串
        ocr_text = " ".join(sorted_lines)
        screw_models = re.findall(r'\b[A-Z]\b', ocr_text)
        # 使用正则表达式匹配所有包含数字的字符串
        counts = re.findall(r'\d+', ocr_text)

        # 生成结果列表
        result = []
        for model, count in zip(screw_models, counts):
            result.append({
                'key': time.time(),
                'type': model,
                'count': int(count)
            })
        if not result:
            default_time = time.time()
            result = [
                {'key': default_time, 'type': 'A', 'count': 0},
                {'key': default_time, 'type': 'B', 'count': 0},
                {'key': default_time, 'type': 'C', 'count': 0}
            ]
        return result

    # 找到包含最多单独大写字母的行作为型号行
    max_uppercase_count = 0
    model_line = ''
    model_index = -1

    for index, line in enumerate(text):
        words = line.split()
        # 计算单独大写字母的数量
        uppercase_count = sum(1 for word in words if len(word) == 1 and word.isupper())
        if uppercase_count > max_uppercase_count:
            max_uppercase_count = uppercase_count
            model_line = line
            model_index = index

    # 分割型号行
    models = [word for word in model_line.split() if len(word) == 1 and word.isupper()]
    total_count = len(model_line.split())  # 计算所有元素的数量
    if total_count == 0:
        default_time = time.time()
        result = [
            {'key': default_time, 'type': 'A', 'count': 0},
        ]
        return result

    if max_uppercase_count / total_count <= 0.5:
        print("螺丝包为列排列:", model_line)
        # 使用每行的第一个单独的大写英文字母作为型号，最后的数字作为数量
        result = []
        for line in text:
            model_match = re.search(r'\b[A-Z]\b', line)
            count_match = re.findall(r'\d+', line)
            if model_match and count_match:
                result.append({
                    'key': time.time(),
                    'type': model_match.group(),
                    'count': int(count_match[-1])
                })
        if not result:
            default_time = time.time()
            result = [
                {'key': default_time, 'type': 'A', 'count': 0},
                {'key': default_time, 'type': 'B', 'count': 0},
                {'key': default_time, 'type': 'C', 'count': 0}
            ]
        return result

    # 提取数量行（假设数量行紧跟在型号行之后）
    if model_index + 1 >= len(text):
        print("没有找到数量行")
        default_time = time.time()
        result = [
            {'key': default_time, 'type': 'A', 'count': 0},
            {'key': default_time, 'type': 'B', 'count': 0},
            {'key': default_time, 'type': 'C', 'count': 0}
        ]
        return result

    counts = text[model_index + 1].split()
    counts = [re.search(r'\d+', count_text).group() if re.search(r'\d+', count_text) else '0' for count_text in counts]

    # 补全数量行
    while len(counts) < len(models):
        counts.append('0')
    if len(counts) > len(models):
        counts = counts[:len(models)]

    # 生成结果列表
    result = []
    for model, count_text in zip(models, counts):
        if not model.isalpha() or not model.isupper():
            continue
        count = int(count_text)
        result.append({
            'key': time.time(),
            'type': model,
            'count': count
        })

    if not result:
        default_time = time.time()
        result = [
            {'key': default_time, 'type': 'A', 'count': 0},
            {'key': default_time, 'type': 'B', 'count': 0},
            {'key': default_time, 'type': 'C', 'count': 0}
        ]

    return result


def get_Screw_bags(file, page_number, rect):
    doc = fitz.open(file)
    result = extract_Screw_bags(doc, page_number, rect)
    result = sorted(result, key=lambda x: x['type'])
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
def replace_special_chars(text):
    # 替换 'z' 或 'Z' 在 'x' 或 'X' 之后或大写字母前的情况
    result = re.sub(r'(?i)(z)(?=(x|[A-Z]))', '2', text)
    result = re.sub(r'(?i)(?<=x)(z)', '2', result)

    # 替换 'i' 在 'x' 或 'X' 之后或大写字母前的情况
    result = re.sub(r'(?i)(i)(?=(x|[A-Z]))', '1', result)
    result = re.sub(r'(?i)(?<=x)(i)', '1', result)

    return result

def ocr_below_rect(doc, page_number, rect):
    # 创建OCR reader，假设使用英文
    reader = easyocr.Reader(['en'])
    # 加载指定页面
    page = doc.load_page(page_number - 1)
    # 计算矩形的底边界
    bottom_y = rect[1] + rect[3]
    # 获取页面的尺寸
    page_height = page.rect.height
    # 定义从矩形底部到页面底部的区域
    clip_rect = fitz.Rect(0, bottom_y, page.rect.width, page_height)
    # 获取区域图像
    pix = page.get_pixmap(clip=clip_rect)
    # 将图像数据转换为OpenCV格式的numpy数组
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:  # 有时图片是RGBA需要转换为RGB
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    # 使用EasyOCR进行文本识别
    results = reader.readtext(img)
    # 提取识别的文本内容并合并成一个字符串
    texts = ' '.join([result[1] for result in results])
    return texts

def text_below_rect(doc, page_number, rect):
    # 页面索引从0开始，因此需要减1
    page = doc.load_page(page_number - 1)

    # 页面的总高度
    page_height = page.rect.height

    # 定义从矩形底部到页面底部的区域
    clip_rect = fitz.Rect(rect[0], rect[1] + rect[3], rect[0] + rect[2], page_height)

    # 提取该区域的文本
    text_list = extract_text_from_page(doc, page_number-1, clip_rect)
    return text_list

def get_step_screw(doc, pages, result_dict, rect_page, rect):
    rect_page = rect_page + 1
    print(f"螺丝包页为: {rect_page}")
    # 提取字典键并去除空格
    keys = [key.strip() for key in result_dict.keys()]

    # 将键转换为字符类用于正则表达式
    key_pattern = '[' + ''.join(keys) + ']'
    # 构建正则表达式，包括所有提取的键
    pattern = fr'(\d+)\s*[×xX*]\s*({key_pattern})|({key_pattern})\s*[×xX*]\s*(\d+)'
    image_page = []
    letter_counts = {}
    letter_pageNumber = {}
    letter_count = {}

    for page_num in pages:
        page = doc.load_page(page_num - 1)
        if rect_page == page_num:
            print(f"第{page_num}和螺丝包相同")
            text_list = text_below_rect(doc, page_num, rect)
            print(f"第{page_num}页，提取到的文字为{text_list}")
            text = '\n'.join(text_list)
        else:
            text_list = extract_text_from_page(doc, page_num - 1)
            print(f"第{page_num}页，提取到的文字为{text_list}")
            text = '\n'.join(text_list)

        # text = extract_text_from_pdf(doc, page_num)
        matches = re.findall(pattern, text)
        print(f"matches:{matches}matches")
        if len(matches) == 0:
            if page_num == rect_page:
                print(f"第{page_num}和螺丝包相同")
                text = ocr_below_rect(doc, page_num, rect)
            else:
                text = extract_text_from_pdf(doc, page_num)
            print(f"{page_num}可能是图片，开始ocr识别")
            text = replace_special_chars(text)
            print(f"{page_num}:{text}")
            matches = re.findall(pattern, text)
            image_page.append(page_num)
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

    return letter_counts, letter_pageNumber, letter_count, image_page


def check_total_and_step(doc, result_dict, step_page, rect_page, rect):
    count_mismatch = {}  # 数量不匹配的情况

    letter_counts, letter_pageNumber, letter_count, image_page = get_step_screw(
        doc, step_page, result_dict, rect_page, rect)

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

    return count_mismatch, letter_count, letter_pageNumber, result_dict, image_page


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
def check_screw(username, file, filename, table, start, end, page, rect):
    print("---begin check_screw---")
    print(f"username : {username}")
    doc = fitz.open(file)
    # 获取螺丝包
    result_dict = {item['type']: item['count'] for item in table}
    print("Screw bag:", result_dict)
    step_page = list(range(start, end + 1))
    if start < 1 or end > doc.page_count:
        return CODE_ERROR, {}, '请检查步骤页输入是否正确'
    count_mismatch, letter_count, letter_pageNumber, result_dict, image_page = check_total_and_step(
        doc, result_dict, step_page, page, rect)
    mismatch_dict, match_dict = create_dicts(
        result_dict, count_mismatch, letter_count, letter_pageNumber)

    print("Mismatch Dict:", mismatch_dict)
    print("Match Dict:", match_dict)
    result = mismatch_dict+match_dict
    data = {
        'result': result,
        'image_page': image_page
    }
    print("save file")
    save_Screw(username['username'], CODE_SUCCESS, file,
               mismatch_dict, match_dict, image_page, '')
    print("save success")
    doc.close()
    print("---end check_screw---")
    return CODE_SUCCESS, data, None


class ScrewHandler(MainHandler):
    @run_on_executor
    def process_async1(self, file, page_number, rect):
        return get_Screw_bags(file, page_number, rect)

    @run_on_executor
    def process_async2(self, username, file, filename, table, start, end,page, rect):
        return check_screw(username, file, filename, table, start, end, page, rect)
    async def post(self):
        if self.request.path == "/api/screw/bags":
            param = tornado.escape.json_decode(self.request.body)
            rect = param['rect']
            page = param['page']
            file = param['file_path']
            # 修改宽度 (w) 和高度 (h)
            rect = [value * 72 / 300 for value in rect]
            code, data, msg = await self.process_async1(file, page, rect)
        elif self.request.path == "/api/screw/compare":
            username = self.current_user
            params = tornado.escape.json_decode(self.request.body)
            print(params)
            file = params['file_path']
            table = params['table']
            start = int(params['start'])
            end = int(params['end'])
            rect = params['rect']
            page = params['page']
            rect = [value * 72 / 300 for value in rect]
            file_name = os.path.basename(file)
            print("文件名:", file_name)
            code, data, msg = await self.process_async2(
                username, file, file_name, table, start, end, page, rect)
            data['result'] = sorted(data['result'], key=lambda x: x['type'])
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