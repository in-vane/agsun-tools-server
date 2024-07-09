import os
from datetime import datetime
import base64
from model import db_result, db_line_result_files,  db_area, db_ce, db_ocr, db_diff_pdf
import json
from config import RESULT_FILE_ROOT, IMAGE_ROOT, FLIES_ROOT, FRONT


def create_directory_path(type_id):
    current_year = datetime.now().strftime('%Y')
    current_month_day = datetime.now().strftime('%m')
    current_day = datetime.now().strftime('%d')

    # 创建完整的目录路径
    directory_path = os.path.join(IMAGE_ROOT, current_year, current_month_day, current_day, type_id)
    # 检查并创建目录
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    return directory_path


def save_Diffpdf(username, code, file1_path, file2_path, pages, base64_strings, error_msg, msg):
    if code == 1:
        return
    type_id = '002'
    # 获取存储图片的文件夹
    directory_path = create_directory_path(type_id)

    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    image_paths = []

    for base64_string in base64_strings:
        # 生成时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        image_path = os.path.join(directory_path, f"{timestamp}.png")
        image_path = os.path.normpath(image_path).replace('\\', '/')  # 确保路径为Linux风格
        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))

        image_paths.append(image_path)

    mismatch_str = f"第{pages}页不同"

    # 拼接结果字符串
    if error_msg:
        result = f"{mismatch_str}，{error_msg}"
    else:
        result = mismatch_str

    # 插入图片记录到数据库
    db_diff_pdf.insert_record(username, type_id, file1_path, file2_path, image_paths, result)


def save_language(username, code, file_path, language, msg):
    if code == 1:
        return
    type_id = '008'

    # 初始化一个空列表用于存储错误信息
    errors = []
    # 遍历每个语言信息
    for lang_info in language:
        if lang_info['error']:
            # 生成错误信息并添加到错误列表中
            errors.append(
                f"该文档语言目录{lang_info['language']}不准确，正文{lang_info['page_number']}是{lang_info['actual_language']}")

    # 如果错误列表为空，则表示所有语言顺序正确
    if not errors:
        result = '该文档语言顺序正确'
    else:
        # 否则将所有错误信息拼接成一个字符串
        result = '，'.join(errors)

    # 保存文字记录
    db_result.insert_record(username, type_id, file_path, '', result)


def save_Screw(username, code, file_path, mismatch_dict, match_dict, image_page, msg):
    if code == 1:
        return
    type_id = '005'
    # 检查两个列表是否为空
    if not mismatch_dict and not image_page:
        result = '该文档螺丝无错误'
    elif not mismatch_dict and image_page:
        result = f'该文档的{image_page}页为图片，请仔细检查'
    elif mismatch_dict and not image_page:
        # 构建不匹配螺丝信息字符串
        result_list = []
        for mismatch in mismatch_dict:
            result_list.append(
                f'螺丝{mismatch["type"]}，螺丝包{mismatch["total"]}个，步骤螺丝{mismatch["step_total"]}个，分别在{mismatch["step_page_no"]}页出现{mismatch["step_count"]}个')
        result = '，'.join(result_list)
    else:
        # 当两个列表都不为空时，结合两个结果
        mismatch_result_list = []
        for mismatch in mismatch_dict:
            mismatch_result_list.append(
                f'螺丝{mismatch["type"]}，螺丝包{mismatch["total"]}个，步骤螺丝{mismatch["step_total"]}个，分别在{mismatch["step_page_no"]}页出现{mismatch["step_count"]}个')
        mismatch_result = '，'.join(mismatch_result_list)
        image_result = f'该文档的{image_page}页为图片，请仔细检查'
        result = f'{mismatch_result}，{image_result}'


    # 保存文字记录
    db_result.insert_record(username, type_id, file_path, '', result)


def save_Page_number(username, code, file_path, error, error_page, note, result, msg):
    if code == 1:
        return
    type_id = '004'
    # 获取存储图片的文件夹
    directory_path = create_directory_path(type_id)
    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    image_paths = []

    for base64_string in result:
        # 生成时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        image_path = os.path.join(directory_path, f"{timestamp}.png")
        image_path = os.path.normpath(image_path).replace('\\', '/')  # 确保路径为Linux风格

        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))
        image_paths.append(image_path)

    if not error:
        text = note
    else:
        error_pages_str = ', '.join(map(str, error_page))
        text = f"[{error_pages_str}]页，{note}"

    # 插入记录到数据库
    db_result.insert_record(username, type_id, file_path, image_paths, text)


def save_Line(username, doc, file_path, filename, code, msg):
    type_id = '010'
    # 检查结果文件夹是否存在，不存在则创建
    if not os.path.exists(RESULT_FILE_ROOT):
        os.makedirs(RESULT_FILE_ROOT)
    # 定义保存路径，使用时间戳作为文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    output_path = os.path.join(RESULT_FILE_ROOT, f'{timestamp}.pdf')
    output_path = os.path.normpath(output_path).replace('\\', '/')  # 确保路径为Linux风格
    # 将 doc 保存到指定路径
    doc.save(output_path)

    # 保存数据库
    db_line_result_files.insert_file_record(username, type_id, file_path, output_path)

    # 返回保存路径
    return output_path


def save_ce(username, code, file1_path, file2_path, excel_image_base64, pdf_image_base64):
    if code == 1:
        return
    type_id = '006'
    # 获取存储图片的文件夹
    directory_path = create_directory_path(type_id)

    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    image_paths = []
    base64_strings = []
    base64_strings.append(excel_image_base64)
    base64_strings.append(pdf_image_base64)
    for base64_string in base64_strings:
        # 生成时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        image_path = os.path.join(directory_path, f"{timestamp}.png")
        image_path = os.path.normpath(image_path).replace('\\', '/')  # 确保路径为Linux风格
        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))

        image_paths.append(image_path)

    # 插入图片记录到数据库
    db_ce.insert_record(username, type_id, file1_path, file2_path, image_paths)


def save_ce_size(username, code, file_path, is_error, message, img_base64, msg):
    if code == 1:
        return
    type_id = '007'
    # 获取存储图片的文件夹
    directory_path = create_directory_path(type_id)

    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    image_paths = []
    base64_strings = []
    base64_strings.append(img_base64)
    for base64_string in base64_strings:
        # 生成时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        image_path = os.path.join(directory_path, f"{timestamp}.png")
        image_path = os.path.normpath(image_path).replace('\\', '/')  # 确保路径为Linux风格
        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))

        image_paths.append(image_path)

    text = message

    # 保存记录
    db_result.insert_record(username, type_id, file_path, image_paths, text)


def save_part_count(username, md5, code, data, msg):
    if code == 1 or len(data.get("error_pages")) ==0:
        return
    type_id = '003'
    print(username, md5, code, data, msg)
    note = data.get("note")
    mapping_results = data.get("mapping_results")
    error_pages = data.get("error_pages")
    image = error_pages[0]
    page = error_pages[1]
    # 获取存储图片的文件夹
    directory_path = create_directory_path(type_id)
    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    image_paths = []

    for base64_string in image:
        # 生成时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        image_path = os.path.join(directory_path, f"{timestamp}.png")
        image_path = os.path.normpath(image_path).replace('\\', '/')  # 确保路径为Linux风格
        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))

        image_paths.append(image_path)



    if not mapping_results and not error_pages:
        text = note

    # Extract error parts from mapping_results
    error_parts = [
        f"零件{result[0]}的爆炸图有{result[2]}个而明细表有{result[3]}个"
        for result in mapping_results if not result[1]
    ]

    # Extract error pages from error_pages
    error_page_numbers = error_pages[1] if len(error_pages) > 1 else []

    # Construct the text
    error_parts_text = "，".join(error_parts)
    error_pages_text = f"第 {error_page_numbers}页的明细表错误" if error_page_numbers else ""

    text = f"爆炸图{error_parts_text}。{error_pages_text}，{note}"
    # 保存文字记录
    db_result.insert_record(username, type_id, md5, image_path, text)


def save_area(username, code, file1_path, file2_path, image_one, image_two, image_result, msg):
    if code == 1:
        return
    type_id = '001'
    # 获取存储图片的文件夹
    directory_path = create_directory_path(type_id)
    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        # 获取当前时间戳
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')

    # 移除 base64 前缀并解码，保存图片
    image_one_path = os.path.join(directory_path, f"{timestamp}_one.png")
    image_one_path = os.path.normpath(image_one_path).replace('\\', '/')  # 确保路径为Linux风格
    img_data_one = base64.b64decode(image_one.split(",")[1])
    with open(image_one_path, 'wb') as f:
        f.write(img_data_one)

    image_two_path = os.path.join(directory_path, f"{timestamp}_two.png")
    image_two_path = os.path.normpath(image_two_path).replace('\\', '/')  # 确保路径为Linux风格
    img_data_two = base64.b64decode(image_two.split(",")[1])
    with open(image_two_path, 'wb') as f:
        f.write(img_data_two)

    image_result_path = os.path.join(directory_path, f"{timestamp}_result.png")
    image_result_path = os.path.normpath(image_result_path).replace('\\', '/')  # 确保路径为Linux风格
    img_data_result = base64.b64decode(image_result.split(",")[1])
    with open(image_result_path, 'wb') as f:
        f.write(img_data_result)
        # 插入数据库记录
    db_area.insert_record(username, type_id, file1_path, file2_path, image_one_path, image_two_path, image_result_path)


def save_ocr(username, doc, md5, page_num, image_one, data):
    type_id = '009'
    # 获取存储图片的文件夹
    image = data.get("result")

    directory_path = create_directory_path(type_id)
    # 确保目录存在
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    # 移除 base64 前缀并解码，保存图片
    image_one_path = os.path.join(directory_path, f"{timestamp}_one.png")
    img_data_one = base64.b64decode(image_one.split(",")[1])
    with open(image_one_path, 'wb') as f:
        f.write(img_data_one)
    image_paths = []
    for base64_string in image:
        # 生成时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        image_path = os.path.join(directory_path, f"{timestamp}.png")
        image_path = os.path.normpath(image_path).replace('\\', '/')  # 确保路径为Linux风格
        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))
        image_paths.append(image_path)

    db_ocr.insert_record(username, type_id, md5, image_one_path, image_path)






