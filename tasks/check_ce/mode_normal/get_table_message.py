import re
import time
import tabula
import pandas as pd
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
            first_cell_value = row[table_start_column - 1].value  # Get the value of the first column of the table
            red_texts = []
            for cell in row[table_start_column:]:
                if cell.font and cell.font.color and cell.font.color.rgb == 'FFFF0000':  # Look for red font
                    red_texts.append(cell.value)  # Add the red font value to the list

            if red_texts:
                # If the key is already in the dictionary, append the new red text value
                if first_cell_value in red_text_dict:
                    red_text_dict[first_cell_value].extend(red_texts)
                else:
                    # Otherwise, create a new key in the dictionary
                    red_text_dict[first_cell_value] = red_texts

    print(red_text_dict)
    red_text_dict = update_key_standard_dict(red_text_dict)
    return red_text_dict


def update_key_standard_dict(data_dict):
    """
    对get_standard_document_as_dict函数获取到字典再处理下，
    的将字典中值为xxxx-xx的键设为CE-sign
    :param data_dict:一个字典
    :return:修改后的字典
    """
    # Define the regex pattern for 'xxxx-xx'
    ce_sign_pattern = re.compile(r'\b\d{4}-\d{2}\b')

    # Create a new dictionary to store updated results
    updated_dict = {}

    # Iterate over items in the original dictionary
    for key, values in data_dict.items():
        # Assume each key only has one value in the list
        if values and ce_sign_pattern.match(values[0]):
            # If the value matches the pattern, change the key to 'CE-sign'
            updated_dict['CE-sign'] = values
        else:
            # Otherwise, keep the original key-value pair
            updated_dict[key] = values

    return updated_dict


def extract_table_from_pdf(pdf_path):
    """
    从PDF中提取表格并返回字典。
    键是表格中的第一个单元格的内容，值是随后单元格的内容的列表。

    :param pdf_path: PDF文件的路径
    :return: 表格内容的字典
    """
    # 使用tabula读取PDF文件中的第一页上的表格
    tables = tabula.read_pdf(pdf_path, pages=1, multiple_tables=True)

    # 如果没有表格被找到，返回一个空字典
    if not tables:
        return {}

    # 提取第一个表格（假设表格在第一页）
    table = tables[0]

    # 创建一个字典来存储数据
    table_dict = {}

    # 遍历表格的每一行
    for index, row in table.iterrows():
        # 检查第一个单元格是否为空，如果不为空，则作为键
        if pd.notna(row.iloc[0]):
            key = row.iloc[0]  # 第一个单元格不为空，作为键
            # 使用列表推导式创建值列表，过滤掉nan
            values = [item for item in row.iloc[1:] if pd.notna(item)]
            table_dict[key] = values

    return table_dict


def remove_empty_lists(input_dict):
    """
    删除字典中值列表为空的键值对，并返回一个新的字典。

    :param input_dict: 要处理的字典
    :return: 更新后的字典，其中不包含空列表的键值对
    """
    # 使用字典推导式来创建一个新的字典，其中仅包含非空列表的键值对
    new_dict = {key: value for key, value in input_dict.items() if value}

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
