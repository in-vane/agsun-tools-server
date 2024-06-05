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

        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))

        image_paths.append(image_path)

    data = {
        'pages': pages,
        'error_msg': error_msg,
    }
    # 将 data 转换为字符串
    data_str = json.dumps(data, ensure_ascii=False)
    # 插入图片记录到数据库
    db_diff_pdf.insert_record(username, type_id, file1_path, file2_path, image_paths, data_str)


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
                f"该文档语言目录{lang_info['language']}不准确，正文{lang_info['page_number']}明明是{lang_info['actual_language']}")

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
    # 将 doc 保存到指定路径
    doc.save(output_path)

    # 保存数据库
    db_line_result_files.insert_file_record(username, type_id, file_path, output_path)

    # 返回保存路径
    return output_path


def save_ce(username, code, file1_md5, file2_md5, excel_image_base64, pdf_image_base64, msg):
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

        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))

        image_paths.append(image_path)

    # 插入图片记录到数据库
    db_ce.insert_record(username, type_id, file1_md5, file2_md5, image_paths)


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
    img_data_one = base64.b64decode(image_one.split(",")[1])
    with open(image_one_path, 'wb') as f:
        f.write(img_data_one)

    image_two_path = os.path.join(directory_path, f"{timestamp}_two.png")
    img_data_two = base64.b64decode(image_two.split(",")[1])
    with open(image_two_path, 'wb') as f:
        f.write(img_data_two)

    image_result_path = os.path.join(directory_path, f"{timestamp}_result.png")
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

        # 清理 base64 字符串，去掉前面的 data:image/png;base64, 部分
        img_base64_cleaned = base64_string.split(',')[1] if ',' in base64_string else base64_string
        # 解码base64字符串并保存为图片
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(img_base64_cleaned))
        image_paths.append(image_path)

    db_ocr.insert_record(username, type_id, md5, image_one_path, image_path)


def images_to_base64_list(directory_path):
    base64_list = []

    # 获取目录下所有文件
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)

        # 检查是否为文件且扩展名为常见图像格式
        if os.path.isfile(file_path) and file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            with open(file_path, "rb") as image_file:
                # 读取图像文件内容并进行base64编码
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                base64_list.append(f"data:image/{file_name.split('.')[-1]};base64,{encoded_string}")

    return base64_list


# base64_list = images_to_base64_list('image1')

# save_language("username", 0, '123456', [
#     {
#         'language': 'EN',
#         'page_number': [1, 4],
#         'error': False,
#         'actual_language': 'EN'
#     },
#     {
#         'language': 'FR',
#         'page_number': [5, 8],
#         'error': True,
#         'actual_language': 'ES'
#     },
#     {
#         'language': 'DE',
#         'page_number': [9, 12],
#         'error': False,
#         'actual_language': 'DE'
#     }
# ]
# , '')


# save_Screw("username", 0, '231456', [
#         {
#             'type': 'A',
#             'total': 17,
#             'step_total': 15,
#             'step_count': [5, 3, 7],
#             'step_page_no': [2, 4, 6]
#         },
#         {
#             'type': 'B',
#             'total': 18,
#             'step_total': 18,
#             'step_count': [10, 8],
#             'step_page_no': [3, 5]
#         },
#         {
#             'type': 'C',
#             'total': 2,
#             'step_total': 2,
#             'step_count': [1, 1],
#             'step_page_no': [1, 7]
#         },
#         {
#             'type': 'D',
#             'total': 4,
#             'step_total': 3,
#             'step_count': [2, 1],
#             'step_page_no': [8, 10]
#         },
#         {
#             'type': 'E',
#             'total': 4,
#             'step_total': 0,
#             'step_count': [],
#             'step_page_no': []
#         }
#     ], [3,6,5], '')
# save_Page_number("username", 0, '345678', True, [3, 5, 7],'页码错误',base64_list, '')
# save_ce_size("username", 0, '123456', True, "尺寸不一致, 标注为(100 x 50), 检测结果为(98 x 52)", base64_list[0], '')


# import fitz
# doc = fitz.open('D:\\agsun-tools-server\\tasks\\1\ACE 6-14.pdf')
# save_Line("username", doc, '123456', 'ACE 6-14', 0, '')
#


# save_area("username", 0, '123456', base64_list[0], base64_list[1], base64_list[2], '')


# save_Diffpdf("username", 0, 'file1_md5', "file2_md5", [2, 3, 4], base64_list, '', '')

# save_ce("username", 0, "file1_md5", "file2_md5", base64_list[0], base64_list[1], '')


# data = {
#     "mapping_results": [
#         ["1", True, 10, 10],
#         ["2", False, 5, 8]
#     ],
#     "error_pages": [
#         [
#             "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAoAAAAHgCAIAAACThk5UAAAAA3NCSVQICAjb4U/gAAAgAElEQVR4...",
#             "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAoAAAAHgCAIAAACThk5UAAAAA3NCSVQICAjb4U/gAAAgAElEQVR4..."
#         ],
#         [2, 3]
#     ],
#     "note": "零件计数：检测成功\n明细表检测：检测成功,序号 1,2 有误"
# }
# save_part_count("username", "md5", 0, data, '')
