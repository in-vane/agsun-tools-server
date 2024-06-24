import re
import time
import tabula
import pandas as pd
import pdfplumber
from .get_similarity import compare_dictionaries


def get_standard_document_as_dict(wb, sheet_name):
    """
    获取吉森标准ce表的表格红色参数信息
    :param standard_excel: 吉森ce表
    :param sheet_name: excel表内的工作表
    :return: 一个字典
    """
    # Load the Excel file
    # wb = openpyxl.load_workbook(standard_excel)
    # Access the specified sheet
    sheet = wb[sheet_name]

    red_text_dict = {}  # Create a dictionary to store the results

    # Traverse each row
    for row in sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        # Assume the table's first column is not empty and starts from the second column
        table_start_column = None
        for cell in row:
            if cell.value is not None and table_start_column is None:
                table_start_column = cell.column

        # If the start of the table is found
        if table_start_column is not None:
            # Get the value of the first column of the table
            first_cell_value = row[table_start_column - 1].value
            red_texts = []
            for cell in row[table_start_column:]:
                if cell.font and cell.font.color and cell.font.color.rgb == 'FFFF0000':  # Look for red font
                    # Add the red font value to the list
                    red_texts.append(cell.value)

            if red_texts:
                # If the key is already in the dictionary, append the new red text value
                if first_cell_value in red_text_dict:
                    red_text_dict[first_cell_value].extend(red_texts)
                else:
                    # Otherwise, create a new key in the dictionary
                    red_text_dict[first_cell_value] = red_texts

    # print(red_text_dict)
    red_text_dict = update_key_standard_dict(red_text_dict)
    return red_text_dict


def update_key_standard_dict(data_dict):
    """
    对get_standard_document_as_dict函数获取到字典再处理下，
    的将字典中值为xxxx-xx的键设为CE-sign
    :param data_dict:一个字典
    :return:修改后的字典
    """
    # 定义匹配'xxxx-xx'格式的正则表达式
    ce_sign_pattern = re.compile(r'\b\d{4}-\d{2}\b')

    # 创建一个新字典用于存储更新后的结果
    updated_dict = {}

    # 遍历原始字典中的项
    for key, values in data_dict.items():
        # 假设每个键只对应一个值列表中的第一个元素
        values[0] = str(values[0])
        if values and ce_sign_pattern.match(values[0]):
            # 如果值符合模式，则将键改为'CE-sign'
            updated_dict['CE-sign'] = values
        else:
            # 否则，保持原键值对不变
            updated_dict[key] = values

    return updated_dict


def extract_table_from_pdf(pdf_path):
    """
    使用 tabula-py 从 PDF 的第一页提取最大的表格，如果失败则使用 pdfplumber。
    将表格中每行的第一个单元格作为键，其余单元格（非None值）作为值列表存储到字典中。

    :param pdf_path: PDF 文件的路径
    :return: 包含表格数据的字典
    """
    try:
        # 尝试使用 tabula-py 提取 PDF 中的表格
        tables = tabula.read_pdf(pdf_path, pages=1)

        if not tables or tables[0].empty:
            raise ValueError("No tables found with tabula")

        # 假设只有一个表格，获取第一个表格
        table = tables[0]

        table_dict = {}
        for index, row in table.iterrows():  # 遍历表格的每一行
            if row[0]:  # 确保键不为空
                key = str(row[0]).strip()  # 删除可能的前后空白字符
                values = [str(item) for item in row[1:] if item is not None]  # 过滤掉 None 值
                table_dict[key] = values
        clean_dict = {}
        for key, values in table_dict.items():
            if key.lower() != 'nan':
                clean_values = [value for value in values if value.lower() != 'nan']
                if clean_values:  # 仅在值列表不为空时添加到字典
                    clean_dict[key] = clean_values
        print("Extracted using tabula:", clean_dict)
        return clean_dict

    except Exception as e:
        print(f"Tabula extraction failed: {e}")

        # 如果 tabula 失败，使用 pdfplumber 提取表格
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]  # 获取第一页
            table = first_page.extract_table()  # 提取表格

            if not table:
                return {}  # 如果没有表格，返回空字典

            table_dict = {}
            for row in table[1:]:  # 假设第一行是表头，从第二行开始处理数据
                if row[0] is not None:  # 确保键不为None
                    key = row[0].strip()  # 删除可能的前后空白字符
                    values = [item for item in row[1:] if item is not None]  # 过滤掉None值
                    table_dict[key] = values

            print("Extracted using pdfplumber:", table_dict)
            return table_dict


def remove_empty_lists(input_dict):
    """
    删除字典中值列表为空的键值对，并返回一个新的字典。

    :param input_dict: 要处理的字典
    :return: 更新后的字典，其中不包含空列表的键值对
    """
    # 使用字典推导式来创建一个新的字典，其中仅包含非空列表的键值对
    new_dict = {key: [item for item in value if item] for key, value in input_dict.items() if value and any(item for item in value if item)}

    return new_dict


def add_ce_signs_to_dict(doc, input_dict):
    """
    从PDF文件中读取文本，查找所有符合XXXX-XX格式的字符串（X是1到9的数字），
    并将它们作为列表添加到字典中，键为'CE-sign'。

    :param pdf_path: PDF文件的路径
    :param input_dict: 要更新的字典
    :return: None（原地修改字典）
    """

    # 用于存储所有找到的CE标记的列表
    ce_signs = []

    # 正则表达式匹配XXXX-XX模式，其中X是1到9的数字
    pattern = re.compile(r'\b[0-9]{4}-[0-9]{2}\b')

    # 遍历PDF中的每一页
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()

        # 在当前页的文本中查找所有匹配的字符串
        matches = pattern.findall(text)
        ce_signs.extend(matches)
    # 如果找到了匹配的字符串，则更新输入字典
    if ce_signs:
        input_dict['CE-sign'] = ce_signs
    return input_dict


def all(wb, work_table, doc, PDF_PATH1):
    # 假设Excel文件已经保存在以下路径
    # 调用函数并打印结果

    red_text_data = get_standard_document_as_dict(wb, work_table)
    print(f"吉盛标准ce表:{red_text_data}")

    # 调用函数并传入PDF文件的路径
    table_content_dict = extract_table_from_pdf(PDF_PATH1)
    table_content_dict = remove_empty_lists(table_content_dict)
    table_content_dict = add_ce_signs_to_dict(doc, table_content_dict)
    print(f"客户ce表：{table_content_dict}")

    start = time.time()
    red_text_data = compare_dictionaries(red_text_data, table_content_dict)
    print(red_text_data)
    end = time.time()
    print(f"对字典进行匹配耗时{end - start}秒")
    return red_text_data
