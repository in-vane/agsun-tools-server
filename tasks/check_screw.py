import os
import re
import csv
import shutil
from io import BytesIO
import fitz
import pandas as pd
from tabula import read_pdf


from save_filesys_db import save_Screw

PDF_PATH = './assets/pdf/temp.pdf'
IMAGE_PATH = './assets/image'
CSV_PATH = './assets/selected_table.csv'


CODE_SUCCESS = 0
CODE_ERROR = 1


def find_target_table(doc):
    total_pages = len(doc)  # 获取PDF的总页数

    # 遍历每一页
    for page_num in range(1, total_pages + 1):
        # 使用tabula读取当前页的表格
        df_list = read_pdf(PDF_PATH, pages=page_num, multiple_tables=True)

        for df in df_list:
            # 检查表头和内容是否符合预期
            if all(x in df.columns for x in ['A', 'B', 'C']) and 'x' in ''.join(df.iloc[:, 1].astype(str)):
                df.to_csv(CSV_PATH, index=False)  # 找到符合条件的表格，保存为CSV文件
                return page_num
    return None


# 处理每个单元格数据
def clean_cell(cell):
    if isinstance(cell, str):
        # 移除"x"并保留数字
        cell = re.sub(r'x(\d+)', r'\1', cell)
        # 保留只包含一个大写字母或数字的单元格内容
        if re.match(r'^[A-Z]$', cell) or re.match(r'^\d+$', cell):
            return cell
    return None


# 获取大写英问字符和对应数字
def manage_csv():
    # 尝试读取CSV文件，假设它位于可以访问的路径
    try:
        df = pd.read_csv(CSV_PATH, header=None)
        # 应用清理函数到每个单元格
        df = df.applymap(clean_cell)
        # 删除全为空的列
        df.dropna(axis=1, how='all', inplace=True)
        # 覆盖原来的CSV文件
        df.to_csv(CSV_PATH, index=False, header=False)
    except Exception:
        pass


# csv转字典
def read_csv_to_dict():
    result_dict = {}

    with open(CSV_PATH, 'r', encoding='utf-8') as csv_file:
        # 使用 csv.reader 读取 CSV 文件
        csv_reader = csv.reader(csv_file)

        # 读取第一行为字符，第二行为数字
        characters = next(csv_reader)
        numbers = next(csv_reader)

        # 清理 numbers 列表，确保只包含数字
        cleaned_numbers = []
        for item in numbers:
            # 提取字符串中的数字部分
            match = re.search(r'\d+', item)
            if match:
                cleaned_numbers.append(int(match.group(0)))
            else:
                cleaned_numbers.append(0)  # 如果没有找到数字，使用0作为默认值

        # 将字符和数字对应存储到字典中
        result_dict = dict(zip(characters, cleaned_numbers))

    return result_dict


# 如果连续超过4张页面为矢量页面，认为为步骤页，提取步骤页
def detect_vector_pages(doc):
    step_pages = []  # 用于存储步骤页的列表
    temp_start = None  # 临时变量，用于记录当前连续序列的起始页
    last_page = None  # 记录上一个矢量图页面的页码

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        vector_count = len(page.get_drawings())

        # 当前页面是矢量图，并且是连续的
        if vector_count > 1000:
            if temp_start is None:
                temp_start = page_num  # 开始新的连续序列
            last_page = page_num
        else:
            # 不是矢量图或不连续
            if last_page is not None and (last_page - temp_start) >= 3:
                # 如果连续序列的长度至少为4，则记录这个范围
                step_pages.extend(
                    range(temp_start + 1, last_page + 2))  # 页码从1开始
            # 重置连续序列的起始和结束页
            temp_start = None
            last_page = None
    # 检查最后一段连续序列
    if last_page is not None and (last_page - temp_start) >= 3:
        step_pages.extend(range(temp_start + 1, last_page + 2))
    print(step_pages)
    return step_pages
# 提取步骤页，需要的步骤螺丝


def extract_text_meeting_pattern(doc, pages):

    pattern = r'(\d+)\s*[xX]\s*([A-Z])'
    letter_counts = {}
    letter_pageNumber = {}
    letter_count = {}

    for page_num in pages:
        page = doc.load_page(page_num - 1)  # Page numbering starts from 0
        text = page.get_text()
        matches = re.findall(pattern, text)
        for match in matches:
            count, letter = match
            count = int(count)

            # Update letter_counts
            if letter not in letter_counts:
                letter_counts[letter] = count
            else:
                letter_counts[letter] += count

            # Update letter_pageNumber
            if letter not in letter_pageNumber:
                letter_pageNumber[letter] = [page_num]
            elif page_num not in letter_pageNumber[letter]:
                letter_pageNumber[letter].append(page_num)

            # Update letter_count
            if letter not in letter_count:
                letter_count[letter] = [count]
            else:
                letter_count[letter].append(count)

    print("letter_counts:", letter_counts)
    print("letter_pageNumber:", letter_pageNumber)
    print("letter_count:", letter_count)

    return letter_counts, letter_count, letter_pageNumber


# 获取步骤螺丝
def get_step_screw(doc):
    # 提取步骤下方的图像
    step_page = detect_vector_pages(doc)
    letter_counts, letter_count, letter_pageNumber = extract_text_meeting_pattern(
        doc, step_page)

    return letter_counts, letter_count, letter_pageNumber


def check_total_and_step(doc, result_dict, page_num):
    count_mismatch = {}  # 数量不匹配的情况
    extra_chars = {}  # 多余的字符
    missing_chars = {}  # 缺少的字符

    letter_counts, letter_count, letter_pageNumber = get_step_screw(doc)

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
            extra_chars[key] = letter_counts[key]

    # 检查result_dict是否有letter_counts没有的字符,多余的种类螺丝
    for key in result_dict:
        if key not in letter_counts:
            print(f"缺少的字符: {key} 在 letter_counts 中不存在")
            missing_chars[key] = result_dict[key]

    return count_mismatch, letter_count, letter_pageNumber, result_dict


def create_dicts(result_dict, count_mismatch, letter_count, letter_pageNumber):
    mismatch_dict = []
    match_dict = []

    for key, value in count_mismatch.items():
        mismatch_dict.append({
            'type': key,
            'total': value['expected'],
            'step_total': value['actual'],
            'step_count': letter_count[key],
            'step_page_no': letter_pageNumber[key]
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
def check_screw(username, file, filename):
    # doc = fitz.open(file)
    doc = fitz.open(stream=BytesIO(file))
    doc.save(PDF_PATH)
    if not os.path.isdir(IMAGE_PATH):
        os.makedirs(IMAGE_PATH)
    # 获取螺丝包
    page_num = find_target_table(doc)
    if page_num is None:
        msg = '未检测到有螺丝包'
        print(msg)
        save_Screw(username, doc, filename, CODE_SUCCESS, [], [], msg)
        return CODE_ERROR, {}, msg
    manage_csv()
    result_dict = read_csv_to_dict()
    count_mismatch, letter_count, letter_pageNumber, result_dict = check_total_and_step(
        doc, result_dict, page_num)
    mismatch_dict, match_dict = create_dicts(
        result_dict, count_mismatch, letter_count, letter_pageNumber)

    print(f"count_mismatch = {count_mismatch}")
    print("Mismatch Dict:", mismatch_dict)
    print("Match Dict:", match_dict)

    os.remove(CSV_PATH)
    os.remove(PDF_PATH)
    shutil.rmtree(IMAGE_PATH)
    data = {
        'mismatch_dict': mismatch_dict,
        'match_dict': match_dict
    }
    save_Screw(username, doc, filename, CODE_SUCCESS,
               mismatch_dict, match_dict, None)
    doc.close()
    return CODE_SUCCESS, data, None


# 测试
# def pdf_to_bytes(file_path):
#     with open(file_path, 'rb') as file:
#         bytes_content = file.read()
#     return bytes_content
# file1 = 'page_number/Screw_dui.pdf' # 请根据实际情况修改路径
# file1 = pdf_to_bytes(file1)
# check_screw(file1)
