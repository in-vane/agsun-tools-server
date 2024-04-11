from io import BytesIO
from PIL import Image
import base64
import os
from datetime import datetime
from model import *
from openpyxl import load_workbook

# 全局变量定义
ROOT = '/home/zhanghantao/agsun-tools-server/db'
# 动态设置基础目录的函数
def setup_directory_paths(userinfo, base_dir):
    current_year = datetime.now().strftime('%Y')
    current_month_day = datetime.now().strftime('%m%d')
    current_time = datetime.now().strftime('%H-%M-%S')
    unique_identifier = userinfo['username']  # 根据实际情况动态赋值
    print(base_dir, current_year,
                           current_month_day, current_time, unique_identifier)
    pdf_dir = os.path.join(base_dir, current_year,
                           current_month_day, current_time, unique_identifier)
    result_dir = os.path.join(pdf_dir, 'result')
    result_file_path = os.path.join(result_dir, 'result.txt')
    image_result_dir = os.path.join(result_dir, 'image')

    return pdf_dir, result_dir, result_file_path, image_result_dir


def images_to_directory(base64_images, image_result_dir):
    """
    将Base64编码的图像列表转换为图像并保存到指定目录。

    :param base64_images: 包含Base64编码图像的字符串列表。
    :param image_result_dir: 输出图像的目录。
    """
    # 确保输出目录存在
    if not os.path.exists(image_result_dir):
        os.makedirs(image_result_dir)

    for idx, base64_str in enumerate(base64_images, start=1):
        # 移除"data:image/jpeg;base64,"部分，仅解码Base64编码的数据
        img_data = base64.b64decode(base64_str.split(",")[1])

        # 使用BytesIO将二进制数据转换成图像
        image = Image.open(BytesIO(img_data))

        # 构建输出文件路径
        output_path = os.path.join(image_result_dir, f"error_page_{idx}.jpeg")

        # 保存图像到文件系统
        image.save(output_path)
        print(f"Saved: {output_path}")


def save_Screw(username, doc, base_file_name, code, mismatch_dict, match_dict, msg):
    base_dir = f'{ROOT}/001'
    pdf_dir, result_dir, result_file_path, image_result_dir = setup_directory_paths(
        username,base_dir)
    # 确保PDF和结果目录存在
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    # 保存文件系统
    # 动态设置PDF输出路径
    pdf_output_path = os.path.join(pdf_dir, f'{base_file_name}')
    doc.save(pdf_output_path)  # 使用动态生成的路径保存文件
    # 如果存在错误，则保存问题列表
    if code == 1:
        is_error = 1
        with open(result_file_path, 'w') as result_file:
            result_file.write(msg)
    else:
        if mismatch_dict is []:
            is_error = 1
            with open(result_file_path, 'w') as result_file:
                for item in mismatch_dict:
                    # Extract the necessary information from the current item
                    model_type = item['type']
                    total_screws = item['total']
                    step_total = item['step_total']
                    step_counts = item['step_count']
                    step_page_no = item['step_page_no']
                    # Construct the string for the current item
                    result = f"型号{model_type}螺丝，螺丝包螺丝有{total_screws}个，而步骤螺丝总和有{step_total}，分别在" + \
                             "，".join(f"{page}页出现{count}个" for page,
                                      count in zip(step_page_no, step_counts))
                    result_file.write(result)
        else:
            is_error = 0
            with open(result_file_path, 'w') as result_file:
                result_file.write(f'该文件螺丝包没错\n')

    # 保存数据库
    dataline = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf_path = os.path.join(pdf_dir, f'{base_file_name}')
    pdf_name = f'{base_file_name}'
    result_path = result_dir
    # 创建实例并保存到数据库
    check_pagenumber_instance = CheckScrew(
        username=username,
        dataline=dataline,
        work_num='001',  # 这里需要根据实际情况赋值
        pdf_path=pdf_path,
        pdf_name=pdf_name,
        result=result_path,
        is_error=is_error
    )
    check_pagenumber_instance.save_to_db()


def save_PageNumber(username, doc, base_file_name, code, is_error, issues, error_pages_base64, msg):
    base_dir = f'{ROOT}/002'
    pdf_dir, result_dir, result_file_path, image_result_dir = setup_directory_paths(username,
        base_dir)
    # 确保PDF和结果目录存在
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    # 保存文件系统
    # 动态设置PDF输出路径
    pdf_output_path = os.path.join(pdf_dir, f'{base_file_name}')
    doc.save(pdf_output_path)  # 使用动态生成的路径保存文件
    # 如果存在错误，则保存问题列表
    if code == 1:
        with open(result_file_path, 'w') as result_file:
            result_file.write(msg)
    else:
        if is_error:
            with open(result_file_path, 'w') as result_file:
                for issue in issues:
                    result_file.write(f'{issue}\n')
            images_to_directory(error_pages_base64, image_result_dir)
        else:
            with open(result_file_path, 'w') as result_file:
                result_file.write(f'该文件页码没错\n')
    # 保存数据库
    dataline = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf_path = os.path.join(pdf_dir, f'{base_file_name}')
    pdf_name = f'{base_file_name}'
    result_path = result_dir
    # 创建实例并保存到数据库
    check_pagenumber_instance = CheckPageNumber(
        username=username,
        dataline=dataline,
        work_num='002',  # 这里需要根据实际情况赋值
        pdf_path=pdf_path,
        pdf_name=pdf_name,
        result=result_path,
        is_error=is_error
    )
    
    check_pagenumber_instance.save_to_db()


def save_Language(username, doc, base_file_name, code, language_page, language, msg):
    base_dir = f'{ROOT}/003'
    pdf_dir, result_dir, result_file_path, image_result_dir = setup_directory_paths(
        username,base_dir)
    # 确保PDF和结果目录存在
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    # 保存文件系统
    # 动态设置PDF输出路径
    pdf_output_path = os.path.join(pdf_dir, f'{base_file_name}')
    doc.save(pdf_output_path)  # 使用动态生成的路径保存文件
    # 如果存在错误，则保存问题列表
    if code == 1:
        with open(result_file_path, 'w') as result_file:
            result_file.write(msg)
    else:
        result_str = f"语言目录在第{language_page}页\n"
        for lang in language:
            if not lang['error']:
                result_str += f"正确语言{lang['language']}，{lang['page_number'][0]}页到{lang['page_number'][1]}页\n"
            else:
                result_str += f"错误语言{lang['language']}，{lang['page_number'][0]}页到{lang['page_number'][1]}页，而正文为{lang['actual_language']}\n"
        with open(result_file_path, 'w') as result_file:
            result_file.write(result_str)
    # 保存数据库
    dataline = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf_path = os.path.join(pdf_dir, f'{base_file_name}')
    pdf_name = f'{base_file_name}'
    result_path = result_dir
    # 创建实例并保存到数据库
    if code == 1:
        is_error = 1
    else:
        # Check if any language has error=True
        is_error = any(lang['error'] for lang in language)
    check_pagenumber_instance = CheckLanguage(
        username=username,
        dataline=dataline,
        work_num='003',  # 这里需要根据实际情况赋值
        pdf_path=pdf_path,
        pdf_name=pdf_name,
        result=result_path,
        is_error=is_error
    )
    check_pagenumber_instance.save_to_db()


def save_CE(username, doc, excel_file, name1, name2, work_table, code, image_base64, msg):
    base_dir = f'{ROOT}/004'
    pdf_dir, result_dir, result_file_path, image_result_dir = setup_directory_paths(
        username,base_dir)
    # 确保PDF和结果目录存在
    wb = load_workbook(excel_file)
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    # 保存文件系统
    # 动态设置PDF输出路径
    pdf_output_path1 = os.path.join(pdf_dir, f'{name1}')
    doc.save(pdf_output_path1)  # 使用动态生成的路径保存文件
    pdf_output_path2 = os.path.join(pdf_dir, f'{name2}')
    wb.save(pdf_output_path2)  # 使用动态生成的路径保存文件
    # 如果存在错误，则保存问题列表
    if code:
        with open(result_file_path, 'w') as result_file:
            result_file.write(msg)
    else:
        img_base64 = []
        img_base64.append(image_base64)
        images_to_directory(img_base64, image_result_dir)
    # 保存数据库
    dataline = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf_path = os.path.join(pdf_dir, f'{name1}')
    pdf_name = f'{name1}'
    excel_path = os.path.join(pdf_dir, f'{name2}')
    excel_name = f'{name2}'
    result_path = result_dir
    # 创建实例并保存到数据库
    check_pagenumber_instance = CheckCE(
        username=username,
        dataline=dataline,
        work_num='004',  # 这里需要根据实际情况赋值
        pdf_path=pdf_path,
        pdf_name=pdf_name,
        excel_path=excel_path,
        excel_name=excel_name,
        work_table=work_table,
        result=result_path,
    )
    check_pagenumber_instance.save_to_db()


def save_Diffpdf(username, doc1, doc2, name1, name2, code, mismatch_list, base64_strings, continuous, msg):
    base_dir = f'{ROOT}/005'
    pdf_dir, result_dir, result_file_path, image_result_dir = setup_directory_paths(
        username, base_dir)
    # 确保PDF和结果目录存在
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(result_dir, exist_ok=True)
    # 保存文件系统
    # 动态设置PDF输出路径
    pdf_output_path1 = os.path.join(pdf_dir, f'{name1}')
    pdf_output_path2 = os.path.join(pdf_dir, f'{name2}')
    doc1.save(pdf_output_path1)  # 使用动态生成的路径保存文件
    doc2.save(pdf_output_path2)  # 使用动态生成的路径保存文件
    # 如果存在错误，则保存问题列表
    if code == 1:
        is_error = 1
        with open(result_file_path, 'w') as result_file:
            result_file.write(msg)
    else:
        if mismatch_list is None:
            is_error = 0
            with open(result_file_path, 'w') as result_file:
                result_file.write("这两个pdf对比，一模一样")
        else:
            is_error = 1
            with open(result_file_path, 'w') as result_file:
                for mismatch in mismatch_list:
                    result_file.write(f"{mismatch}\n")
                images_to_directory(base64_strings, image_result_dir)
            if continuous:
                with open(result_file_path, 'w') as result_file:
                    for mismatch in mismatch_list:
                        result_file.write(f"{mismatch}\n")
                    result_file.write(continuous)
                    images_to_directory(base64_strings, image_result_dir)

    # 保存数据库
    dataline = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf_path1 = os.path.join(pdf_dir, f'{name1}')
    pdf_path2 = os.path.join(pdf_dir, f'{name2}')
    pdf_name1 = f'{name1}'
    pdf_name2 = f'{name2}'
    result_path = result_dir
    # 创建实例并保存到数据库
    check_pagenumber_instance = CheckDiffpdf(
        username=username,
        dataline=dataline,
        work_num='005',  # 这里需要根据实际情况赋值
        pdf_path1=pdf_path1,
        pdf_name1=pdf_name1,
        pdf_path2=pdf_path2,
        pdf_name2=pdf_name2,
        result=result_path,
        is_error=is_error
    )
    check_pagenumber_instance.save_to_db()
