import re
import cv2
import pdfplumber
import numpy as np
import base64
import io
import tabula
import fitz
import pandas as pd
from pdf2image import convert_from_path
import math
import os
from PIL import ImageDraw, ImageFont
from save_filesys_db import save_part_count
import easyocr
from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor

os.environ["JAVA_TOOL_OPTIONS"] = "-Djava.awt.headless=true"
DPI = 600
ZOOM = DPI / 72

BASE64_PNG = 'data:image/png;base64,'
# Setting pandas display options
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)


def is_column_increasing(column_data):
    """检查单列数据是否递增"""
    try:
        numeric_data = pd.to_numeric(
            column_data, errors='raise')
        return numeric_data.is_monotonic_increasing
    except ValueError:
        # 如果列包含无法转换为数字的值，则认为该列不是递增的
        return False


def get_error_pages_as_base64(mismatched_details, pdf_path):
    images_base64 = []
    mismatched_page = []
    # 遍历有错误的页码
    for page_number, line_indices in mismatched_details.items():
        images = convert_from_path(
            pdf_path, first_page=page_number - 1, last_page=page_number - 1, fmt='PNG')

        for image in images:
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()

            # 将所有错误行的信息合并成一条信息
            error_lines_info_cn = "序号 " + \
                                  ",".join(map(str, line_indices)) + " 有误"
            error_lines_info_en = "Entry numbers " + \
                                  ",".join(map(str, line_indices)) + \
                                  " are incorrect"
            text_position = (30, 10)  # 在左上角显示信息
            draw.text(text_position, error_lines_info_en,
                      fill=(255, 0, 0), font=font)
            # 将图片转换为Base64编码的字符串
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            images_base64.append(f"{BASE64_PNG}{img_str}")
        mismatched_page.append(page_number)
    return images_base64, mismatched_page, error_lines_info_cn


def convert_to_int(a, b):
    """ 尝试将两个值转换为整数，如果转换失败，保持原值 """
    try:
        a = int(float(a))
    except (ValueError, TypeError):
        pass
    try:
        b = int(float(b))
    except (ValueError, TypeError):
        pass
    return a, b


def find_matching_table_with_pdfplumber(doc, table, exact_pagenumber, num_rows, num_columns, pdf_path, page_pair_index):
    mismatched_pages_list = {}
    # 遍历每一页
    for page_number in range(exact_pagenumber + 1, len(doc.pages)):
        try:
            # 尝试解析指定页面的表格
            tables = tabula.read_pdf(pdf_path, pages=str(page_number), multiple_tables=True)
        except Exception as e:
            # 如果解析过程中出现任何异常，打印错误信息并跳过当前表格
            print(f"解析页面 {page_number} 的表格时发生错误: {e}")
        # 先过滤出尺寸接近要求的表格
        for table_data in tables:
            if not table_data.empty and len(table_data.columns) == len(table.columns):
                # 计算每一行的非 NaN 值的数量
                thresh = math.ceil(len(table_data.columns) * 0.5)  # 设置阈值为列数的一半
                # 删除非 NaN 值少于阈值的行
                table_data = table_data.dropna(thresh=thresh)
                condition_met = False
                # 检查DataFrame是否为空，以及是否满足条件
                if not table_data.empty:
                    try:
                        # 使用 iloc 访问第一行第一列的值
                        first_cell_value = table_data.iloc[0, 0]
                        if first_cell_value is None or first_cell_value == "":
                            condition_met = False
                        else:
                            # 尝试将第一行第一列的值转换为浮点数
                            float(first_cell_value)
                            condition_met = True
                    except ValueError:
                        # 如果转换失败（即不是数字），则认为条件不满足
                        condition_met = False
                    # 如果条件不满足（即第一行看起来像表头），则从第二行开始创建 DataFrame
                    if condition_met:
                        table_data = table_data.reset_index(drop=True)
                    else:
                        # 将第一行设置为表头
                        table_data.columns = table_data.iloc[0]  # 第一行的值成为列名
                        table_data = table_data.drop(
                            table_data.index[0])  # 删除原始的第一行
                        table_data = table_data.reset_index(drop=True)  # 重置索引
                    # 检查调整后的DataFrame的尺寸是否精确符合要求
                    if table_data.shape[0] == num_rows and table_data.shape[1] == num_columns:
                        # 假设我们已经处于需要比较的页面中
                        # 计算需要比较的列索引列表
                        # 初始化一个列表来记录当前页的不匹配行索引
                        current_page_mismatches = []
                        for pair_index in page_pair_index:
                            index_column = int(pair_index['index']) - 1  # 获取index列的索引，减1因为Python索引从0开始
                            count_column = int(pair_index['count']) - 1  # 获取count列的索引，同上
                            # 遍历包含index和count的每一行数据
                            for row_index in range(table.shape[0]):  # 假设table和table_data具有相同的行数
                                expected_index = table.iloc[row_index, index_column]  # 当前行的index值
                                expected_count = table.iloc[row_index, count_column]
                                actual_index = table_data.iloc[row_index, index_column]
                                actual_count = table_data.iloc[row_index, count_column]
                                print(expected_index, expected_count, actual_index, actual_count)
                                # 处理 expected_index 和 actual_index
                                if not pd.isna(expected_index):
                                    expected_index, actual_index = convert_to_int(expected_index, actual_index)
                                    if isinstance(expected_index, int):
                                        if expected_index != actual_index and expected_index not in current_page_mismatches:
                                            current_page_mismatches.append(expected_index)

                                # 处理 expected_count 和 actual_count
                                if not pd.isna(expected_count):
                                    expected_count, actual_count = convert_to_int(expected_count, actual_count)
                                    if isinstance(expected_count, int):
                                        if expected_count != actual_count and expected_index not in current_page_mismatches and not pd.isna(
                                                expected_index):
                                            current_page_mismatches.append(expected_index)
                        # 如果当前页有不匹配的行，更新mismatched_details字典
                        if current_page_mismatches:
                            print(current_page_mismatches)
                            # 页面编号从1开始
                            mismatched_pages_list[page_number +
                                                  1] = current_page_mismatches

    # 获取不匹配页面的图片
    if mismatched_pages_list:
        images_base64, mismatched_pages, error_lines_info = get_error_pages_as_base64(
            mismatched_pages_list, pdf_path)
        return images_base64, mismatched_pages, error_lines_info
    else:
        return [], [], ""


# 定义一个函数来统一边框格式为[x_min, y_min, x_max, y_max]


def unify_bbox_format(bbox):
    x_min = min([point[0] for point in bbox])
    y_min = min([point[1] for point in bbox])
    x_max = max([point[0] for point in bbox])

    y_max = max([point[1] for point in bbox])
    return [x_min, y_min, x_max, y_max]


def get_easy_results(easy_results):
    combined_results = []
    for (bbox, text, prob) in easy_results:
        # EasyOCR返回的bbox是一个四个顶点的列表，格式为：[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        # 我们需要使用unify_bbox_format函数来转换这个格式
        unified_bbox = unify_bbox_format(bbox)
        combined_results.append((unified_bbox, text, prob))
    return combined_results


def get_contour_image(image, min_area=200, max_aspect_ratio=4, min_fill_ratio=0.1):
    # Convert the image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)

    # Perform edge detection using Canny
    edges = cv2.Canny(blurred_image, 10, 200, L2gradient=True)

    # Find contours from the edges
    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area (this threshold can be adjusted)
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    filtered_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        # Calculate the bounding rect and aspect ratio
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        fill_ratio = area / (w * h) if w * h > 0 else 0

        # Filter based on aspect ratio and fill ratio
        if aspect_ratio <= max_aspect_ratio and fill_ratio >= min_fill_ratio:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)

            if len(approx) >= 2:  # Filter out simple geometries
                filtered_contours.append(cnt)

    # or return [largest_contour] if you want to only return the largest one
    return filtered_contours


def save_modified_page_only(doc, page_number, rect):
    """
    仅保存修改后的PDF页面到新文件中。

    :param doc: 输入PDF文件。
    :param output_path: 修改后PDF页面的保存路径。
    :param page_number: 要修改的页面编号（从0开始）。
    :param rect: 保留内容的矩形区域，格式为(x0, y0, x1, y1)。
    """
    page = doc.load_page(page_number)  # 加载指定页面

    # 获取页面上的所有文字块及其位置
    text_instances = page.get_text("dict")["blocks"]

    for instance in text_instances:
        # 检查文字块是否完全在指定矩形内
        inst_rect = fitz.Rect(instance["bbox"])
        if not rect.intersects(inst_rect):
            # 如果文字块在矩形外，标记为需要删除的区域
            page.add_redact_annot(inst_rect)
    page.apply_redactions()  # 应用删除标记，实际删除内容

    # 创建一个新的PDF文档并添加修改后的页面
    new_doc = fitz.open()  # 创建一个新的空白文档
    new_page = new_doc.new_page(-1, width=rect.width,
                                height=rect.height)  # 添加一个新页面，大小与裁剪区域一致

    # 将裁剪区域的内容绘制到新页面上
    clip = rect  # 定义裁剪区域
    new_page.show_pdf_page(new_page.rect, doc, page_number, clip=clip)
    # 将新文档保存到字节流中
    output_stream = io.BytesIO()
    new_doc.save(output_stream)
    new_doc.close()

    # 返回字节流中的数据
    return output_stream.getvalue()


def point_to_line_distance(point, line):
    """
    计算点到直线的距离。
    :param point: 点的坐标 (x, y)。
    :param line: 直线的两个端点 [(x1, y1), (x2, y2)]。
    :return: 点到直线的距离。
    """
    x0, y0 = point
    x1, y1, x2, y2 = line
    # num = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
    den1 = np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    den2 = np.sqrt((x2 - x0) ** 2 + (y2 - y0) ** 2)
    if den1 > den2:
        return den2
    else:
        return den1


def find_closest_line_to_bbox(bbox, lines):
    if lines is None:
        # lines 是 None，没有可迭代的对象，可以返回默认值或进行其他处理
        print("没有线条数据可供处理。")
        return None
    center_point = calculate_center(bbox)
    min_distance = np.inf
    closest_line = None
    margin = 10  # 定义边缘容忍范围为10个像素

    for line in lines:
        x1, y1, x2, y2 = line[0]  # 注意根据实际情况调整直线数据的解包方式
        line_endpoints = (x1, y1, x2, y2)

        # 检查两个端点是否在扩展的bbox内
        inside_first_with_margin = is_point_inside_bbox((x1, y1), bbox, margin)
        inside_second_with_margin = is_point_inside_bbox(
            (x2, y2), bbox, margin)

        # 检查两个端点是否在原始bbox外
        outside_first_without_margin = not is_point_inside_bbox(
            (x1, y1), bbox, -margin)
        outside_second_without_margin = not is_point_inside_bbox(
            (x2, y2), bbox, -margin)

        # 如果两个端点都在边缘容忍范围外，或者一个在内一个在外
        if (outside_first_without_margin and outside_second_without_margin) or \
                (inside_first_with_margin != inside_second_with_margin):
            distance = point_to_line_distance(center_point, line_endpoints)
            if distance < min_distance:
                min_distance = distance
                closest_line = line_endpoints

    return closest_line


def find_farthest_point_from_bbox(bbox, line):
    """
    找到距离bbox中心最远的直线端点。
    :param bbox: 数字的边框 [x_min, y_min, x_max, y_max]。
    :param line: 直线的两个端点 [x1, y1, x2, y2]。
    :return: 距离bbox中心最远的端点 (x, y)。
    """
    digit_center = calculate_center(bbox)
    point1 = (line[0], line[1])
    point2 = (line[2], line[3])

    dist1 = np.linalg.norm(np.array(digit_center) - np.array(point1))
    dist2 = np.linalg.norm(np.array(digit_center) - np.array(point2))

    return point2 if dist2 > dist1 else point1


def extend_line_from_farthest_point(bbox, line, contours):
    """
    从距离bbox中心最远的直线端点开始延长，找到碰到的第一个零件框。
    """
    # 找到距离数字框较远的端点
    farthest_point = find_farthest_point_from_bbox(bbox, line)

    # 计算延长方向
    if farthest_point == (line[0], line[1]):
        direction = (line[0] - line[2], line[1] - line[3])
    else:
        direction = (line[2] - line[0], line[3] - line[1])

    normalized_direction = direction / np.linalg.norm(direction)

    # 初始化延长点
    current_point = np.array(farthest_point, dtype=float)
    max_extension_distance = 500  # 最大延长距离
    extension_distance = 0  # 初始化延长距离计数器
    # 沿反方向延长寻找零件框
    while True:
        current_point += normalized_direction * 10  # 适当调整步长

        # 检查是否碰到零件框
        for contour in contours:
            if cv2.pointPolygonTest(contour, tuple(current_point), False) >= 0:
                return contour  # 找到碰到的零件框

        # 这里可以添加额外的终止条件，例如最大延长距离
        # 更新延长距离计数器
        extension_distance += 10  # 假设每次延长步长为10
        if extension_distance >= max_extension_distance:
            break


def extract_template_with_contour(image, contour):
    x, y, w, h = cv2.boundingRect(contour)
    crop_img = image[y:y + h, x:x + w]

    # 创建一个透明的四通道图像作为模板
    template_adjusted = np.zeros((h, w, 4), dtype=np.uint8)

    # 将裁剪的图像复制到模板的RGB通道
    template_adjusted[..., :3] = crop_img

    # 创建一个掩码，并将模板轮廓内的区域设置为不透明（255）
    mask = np.zeros((h, w), dtype=np.uint8)
    # 首先，绘制一个较粗的轮廓来扩展边缘
    cv2.drawContours(mask, [contour - np.array([x, y])], -1, 255, -1)
    # 将掩码应用到模板的alpha通道
    template_adjusted[..., 3] = mask
    return template_adjusted


def find_and_count_matches(image, filtered_contours, original_contour, threshold=0.9):
    # 确保图像是灰度图
    if len(image.shape) > 2:
        image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        image_gray = image

    # 用于存储形状相似度小于阈值的轮廓数量和匹配到的轮廓列表
    valid_matches = 0
    matched_contours_list = []

    for contour in filtered_contours:
        # 计算当前轮廓与原始轮廓的形状相似度
        similarity = cv2.matchShapes(contour, original_contour, 1, 0.0)
        if similarity < threshold:
            valid_matches += 1
            matched_contours_list.append(contour)

    # 返回匹配数量和匹配到的轮廓列表
    return valid_matches, matched_contours_list


# 定义一个函数来检查序列是否递增
def is_increasing(sequence):
    return all(x < y for x, y in zip(sequence, sequence[1:]))


# 定义一个函数来检查字符串是否包含数字
def contains_number(s):
    return any(char.isdigit() for char in s)


def is_point_inside_bbox(point, bbox, margin=0):
    x, y = point
    xmin, ymin, xmax, ymax = bbox
    return (xmin - margin) <= x <= (xmax + margin) and (ymin - margin) <= y <= (ymax + margin)


def calculate_center(bbox):
    x_min, y_min, x_max, y_max = bbox
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    return (center_x, center_y)


def get_easy_results(easy_results):
    combined_results = []
    for (bbox, text, prob) in easy_results:
        # EasyOCR返回的bbox是一个四个顶点的列表，格式为：[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        # 我们需要使用unify_bbox_format函数来转换这个格式
        unified_bbox = unify_bbox_format(bbox)
        combined_results.append((unified_bbox, text, prob))
    return combined_results


# 定义一个函数来统一边框格式为[x_min, y_min, x_max, y_max]
def unify_bbox_format(bbox):
    x_min = min([point[0] for point in bbox])
    y_min = min([point[1] for point in bbox])
    x_max = max([point[0] for point in bbox])
    y_max = max([point[1] for point in bbox])
    return [x_min, y_min, x_max, y_max]


def get_combined_results(image):
    reader = easyocr.Reader(['en'], gpu=True)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    easy_results = reader.readtext(binary, batch_size=5, detail=1, low_text=0.4, text_threshold=0.4, link_threshold=0.3)
    easy_results = get_easy_results(easy_results)
    # 使用正则表达式来匹配纯数字序列
    digits_regex = re.compile(r'^\d+$')
    # Convert list of results to a dictionary
    number_bboxes = {text: bbox for bbox, text, prob in easy_results if digits_regex.match(text)}
    return image, number_bboxes


def get_image(pdf, page_number, crop_rect):
    output_pdf_bytes = save_modified_page_only(
        pdf, page_number - 1, crop_rect)
    # 将字节流转换为一个BytesIO对象
    output_pdf_stream = io.BytesIO(output_pdf_bytes)
    doc = fitz.open(stream=output_pdf_stream, filetype="pdf")
    page = doc.load_page(0)

    mat = fitz.Matrix(ZOOM, ZOOM)
    pix = page.get_pixmap(matrix=mat)
    # Convert to RGB if not already in RGB format
    if pix.alpha:  # Check if pixmap has an alpha channel
        pix = pix.to_rgb()  # Drop the alpha channel
    # Now, we can be sure that `pix.samples` contains 3 components per pixel (RGB)
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3)
    # 获取页面上的所有文字块及其边界框
    blocks = page.get_text("blocks")

    # 初始化一个字典来存储每个数字序列及其对应的边界框
    number_bboxes = {}
    # 正则表达式，匹配连续的数字
    regex = re.compile(r'\b\d+\b')

    # 遍历所有文字块
    for block in blocks:
        text = block[4]  # 文本内容
        matches = regex.finditer(text)
        for match in matches:
            number_text = match.group()
            if number_text not in number_bboxes:
                # 对于新发现的数字序列，找到其在页面上的位置并记录边界框
                rect = page.search_for(number_text)
                if rect:  # 确保搜索结果非空
                    number_bboxes[number_text] = rect[0]
    # Check if detected text elements are fewer than 5
    if len(number_bboxes) < 5:
        image, number_bboxes = get_combined_results(image)
    doc.close()
    return image, number_bboxes


def get_results(image, number_bboxes):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 应用高斯模糊和Canny边缘检测
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    edges = cv2.Canny(blurred_image, 50, 150)
    # 使用霍夫变换检测直线
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                            threshold=50, minLineLength=100, maxLineGap=25)
    filtered_contours = get_contour_image(image)
    # 初始化字典来存储数字和最近直线的配对关系
    digit_to_part_mapping = {}
    # 遍历每个识别到的数字
    for text, bbox in number_bboxes.items():
        x_min, y_min, x_max, y_max = [int(coord * ZOOM) for coord in bbox]
        bbox = [x_min, y_min, x_max, y_max]
        # 寻找最近的直线
        closest_line = find_closest_line_to_bbox(bbox, lines)
        if closest_line:
            part_contour = extend_line_from_farthest_point(
                bbox, closest_line, filtered_contours)
            if part_contour is not None:
                digit_to_part_mapping[text] = {
                    'part_contour': part_contour, 'bbox': bbox, 'similar_parts_count': 0}
            else:
                # 如果未找到零件框，则更新字典中的相应信息
                digit_to_part_mapping[text] = {
                    'part_contour': None, 'bbox': bbox, 'similar_parts_count': 1}
        else:
            return None
    for digit, info in digit_to_part_mapping.items():
        if 'part_contour' in info and info['part_contour'] is not None:
            # template = extract_template_with_contour(image, info['part_contour'])
            # count = find_and_count_matches(image, template, threshold=0.9)
            count, matched_contours = find_and_count_matches(
                image, filtered_contours, info['part_contour'], threshold=0.05)
            digit_to_part_mapping[digit]['similar_parts_count'] = count
            # 在字典中存储匹配到的轮廓
            digit_to_part_mapping[digit]['matched_contours'] = matched_contours
    return digit_to_part_mapping


def revalidate_matches(image, failed_matches, digit_to_part_mapping, threshold=1):
    revalidated_results = []
    for key, matched, found, expected in failed_matches:
        if not matched:
            if key in digit_to_part_mapping and 'matched_contours' in digit_to_part_mapping[key]:
                matched_contours = digit_to_part_mapping[key]['matched_contours']
                # 初始化匹配成功的计数器
                successful_matches_count = 0
                padding = 5  # 增加的边框尺寸
                for contour in matched_contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    # 提取匹配区域的图像
                    first_template = image[y:y + h, x:x + w]
                    first_template_gray = cv2.cvtColor(
                        first_template, cv2.COLOR_BGR2GRAY)
                    # 首先，确认first_template_gray是否需要增加边框

                    # 提取模板及其alpha通道作为掩码
                    template = extract_template_with_contour(
                        image, digit_to_part_mapping[key]['part_contour'])
                    template_rgb = template[..., :3]
                    template_alpha = template[..., 3]
                    template_gray = cv2.cvtColor(
                        template_rgb, cv2.COLOR_BGR2GRAY)
                    if first_template_gray.shape[0] < template_gray.shape[0] or first_template_gray.shape[1] < \
                            template_gray.shape[1]:
                        # 计算需要增加的高度和宽度
                        delta_height = max(
                            template_gray.shape[0] - first_template_gray.shape[0] + padding, 0)
                        delta_width = max(
                            template_gray.shape[1] - first_template_gray.shape[1] + padding, 0)

                        # 应用边框以增加first_template_gray的尺寸
                        first_template_gray = cv2.copyMakeBorder(first_template_gray,
                                                                 top=delta_height // 2,
                                                                 bottom=delta_height - delta_height // 2,
                                                                 left=delta_width // 2,
                                                                 right=delta_width - delta_width // 2,
                                                                 borderType=cv2.BORDER_CONSTANT,
                                                                 value=[0, 0, 0])  # 使用黑色填充边框
                    first_template_gray = first_template_gray.astype('float32')
                    template_gray = template_gray.astype('float32')
                    # 使用alpha通道作为掩码进行模板匹配
                    res = cv2.matchTemplate(first_template_gray, template_gray, cv2.TM_CCOEFF_NORMED,
                                            mask=template_alpha)
                    _, max_val, _, _ = cv2.minMaxLoc(res)

                    if max_val > threshold:
                        successful_matches_count += 1

                # 检查匹配成功的次数是否与expected值一致
                if successful_matches_count == expected:
                    match_success = True
                    revalidated_results.append(
                        (key, match_success, successful_matches_count, expected))
                else:
                    match_success = False
                    revalidated_results.append(
                        (key, match_success, successful_matches_count, expected))
            else:
                # 如果没有匹配的轮廓，保留原来的匹配失败信息
                revalidated_results.append((key, matched, found, expected))
        else:
            # 如果原本匹配成功，直接添加到结果中
            revalidated_results.append((key, matched, found, expected))

    return revalidated_results


def form_extraction_and_compare(pdf_path, page_number, digit_to_part_mapping, custom_data, page_columns,
                                page_pair_index):
    results = []  # 用于存储比对结果
    table_results = [[], []]
    # 尝试打开PDF文件
    # try:
    with pdfplumber.open(pdf_path) as pdf:
        # 确保页面号码在PDF文档范围内
        if page_number > len(pdf.pages) or page_number < 1:
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': {},
                    'error_pages': [],
                    'note': '明细表页码超出范围',
                },
                'msg': '',
            }
            return custom_data
        # 尝试从指定页面提取表格
        tables = tabula.read_pdf(pdf_path, pages=str(
            page_number), multiple_tables=True)
        # 如果页面上没有表格，返回错误信息
        if not tables:
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': {},
                    'error_pages': [],
                    'note': '在页{}未检测到表格'.format(page_number),
                },
                'msg': '',
            }
            return custom_data
        found_valid_table = False  # 追踪是否找到满足条件的表格
        for table in tables:
            # 检查列数是否是3的倍数，如果是则按每3列分割处理
            num_columns = table.shape[1]
            print(table)
            if num_columns == page_columns and not table.empty:
                # 计算每一行的非 NaN 值的数量
                thresh = math.ceil(len(table.columns)
                                   * 0.5)  # 设置阈值为列数的一半
                # 删除非 NaN 值少于阈值的行
                table = table.dropna(thresh=thresh)
                # 判断第一行第一列是否满足特定条件，这里假设的条件是检查是否为数字
                try:
                    # 假设 sub_table 是之前代码中创建的 DataFrame
                    if not table.empty:
                        first_cell_value = table.iloc[0, 0]
                    else:
                        # 处理空 DataFrame 的情况
                        print("DataFrame 是空的")
                        continue
                    if first_cell_value is None or first_cell_value == "":
                        condition_met = False
                    else:
                        # 尝试将第一行第一列的值转换为浮点数
                        float(first_cell_value)
                        condition_met = True
                except ValueError:
                    # 如果转换失败（即不是数字），则认为条件不满足
                    condition_met = False
                # 如果条件不满足（即第一行看起来像表头），则从第二行开始创建 DataFrame
                if condition_met:
                    table = table.reset_index(drop=True)
                else:
                    # 将第一行设置为表头
                    table.columns = table.iloc[0]  # 第一行的值成为列名
                    table = table.drop(table.index[0])  # 删除原始的第一行
                    table = table.reset_index(drop=True)  # 重置索引

                # 这里假设digit_to_part_mapping字典的key为字符串形式的数字
                found_valid_table = True  # 找到了满足条件的表格
                # 请确保DataFrame的列足够多以支持page_pair_index中的索引
                if not all(0 < int(pair_index['index']) <= len(table.columns) and 0 < int(pair_index['count']) <= len(
                        table.columns) for pair_index in page_pair_index):
                    custom_data['code'] = 1
                    custom_data['data']['note'] = '填写列数值超出表格列的范围。'
                    return custom_data
                for pair_index in page_pair_index:  # 遍历page_pair_index数组
                    key_column = int(pair_index['index']) - 1  # Python索引是从0开始的，所以减1
                    value_column = int(pair_index['count']) - 1  # 同上
                    for key, value in digit_to_part_mapping.items():
                        # 将key_column列中的可转换项转换为整数，无法转换的转为NaN
                        table_copy = table.copy()
                        table_copy[table.columns[key_column]] = pd.to_numeric(table.iloc[:, key_column],
                                                                              errors='coerce').fillna(-1).astype(int)
                        row = table_copy[table_copy.iloc[:, key_column] == int(key)]
                        if len(row) > 1:
                            # 如果有多于一行匹配，记录错误信息
                            custom_data = {
                                'code': 0,
                                'data': {
                                    'mapping_results': {},
                                    'error_pages': [],
                                    'note': '明细表序号重复，无法匹配',
                                },
                                'msg': '',
                            }
                            return custom_data
                        elif len(row) == 1:
                            third_column_value = row.iloc[0, value_column]  # 使用动态指定的value_column而不是固定的第三列
                            if isinstance(third_column_value, str):
                                # 如果是字符串，使用正则表达式提取数字
                                numbers_in_third_column = re.findall(r'\d+', third_column_value)
                            else:
                                # 如果不是字符串，直接将值放入列表
                                numbers_in_third_column = [third_column_value] if pd.notnull(third_column_value) else []
                            if numbers_in_third_column:
                                numbers = [int(num) for num in numbers_in_third_column]
                                if value['similar_parts_count'] not in numbers:
                                    # 匹配失败，返回详细信息
                                    results.append((key, False, value['similar_parts_count'], numbers[0]))
                                else:
                                    results.append((key, True, value['similar_parts_count'], numbers[0]))  # 匹配成功
                            else:
                                # 第value_column列没有找到数字，返回详细信息
                                results.append((key, False, value['similar_parts_count'], None))
                rows, cols = table.shape
                images, mismatches, error_lines_info = find_matching_table_with_pdfplumber(pdf, table, page_number,
                                                                                           num_rows=rows,
                                                                                           num_columns=cols,
                                                                                           pdf_path=pdf_path,
                                                                                           page_pair_index=page_pair_index)
                for i in range(len(images)):
                    table_results[0].append(images[i])
                    table_results[1].append(mismatches[i])
        if (not digit_to_part_mapping) and (all(len(inner) == 0 for inner in table_results)):
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': {},
                    'error_pages': [],
                    'note': '零件计数：爆炸图未检测到数字或直线\n明细表检测：未发现错误',
                },
                'msg': '',
            }
        elif (not digit_to_part_mapping) and (not all(len(inner) == 0 for inner in table_results)):
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': {},
                    'error_pages': table_results,
                    'note': f'零件计数：爆炸图未检测到数字或直线\n明细表检测：检测成功,{error_lines_info}',
                },
                'msg': '',
            }
        elif (not results) and (all(len(inner) == 0 for inner in table_results)):
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': {},
                    'error_pages': [],
                    'note': '零件计数：给定页面表格出错\n明细表检测：未发现错误',
                },
                'msg': '',
            }
        elif (results) and (all(len(inner) == 0 for inner in table_results)):
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': results,
                    'error_pages': [],
                    'note': '零件计数：检测成功\n明细表检测：未发现错误',
                },
                'msg': '',
            }
        elif (not results) and (not all(len(inner) == 0 for inner in table_results)):
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': {},
                    'error_pages': table_results,
                    'note': f'零件计数：给定页面表格出错\n明细表检测：检测成功,{error_lines_info}',
                },
                'msg': '',
            }
        elif (results) and (not all(len(inner) == 0 for inner in table_results)):
            custom_data = {
                'code': 0,
                'data': {
                    'mapping_results': results,
                    'error_pages': table_results,
                    'note': f'零件计数：检测成功\n明细表检测：检测成功,{error_lines_info}',
                },
                'msg': '',
            }

    if not found_valid_table:
        # 所有表格处理完毕，没有找到满足条件的表格
        custom_data = {
            'code': 0,
            'data': {
                'mapping_results': {},
                'error_pages': [],
                'note': '没有找到满足条件的表格',
            },
            'msg': '',
        }
        return custom_data
    return custom_data


def PartCountHandlerOCR(username, file, filename, rect, page_number_explore, page_number_table, page_columns,
                     page_pair_index):
    # pdf_path = f"./assets/pdf/{filename}"
    crop_rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])  # 裁剪区域
    pdf = fitz.open(file)  # 打开PDF文件

    image, bbox = get_image(pdf, page_number_explore, crop_rect)

    custom_data = {
        'code': 0,
        'data': {
            'mapping_results': {},
            'error_pages': [],
            'note': '',
        },
        'msg': '',
    }
    digit_to_part_mapping = get_results(image, bbox)

    custom_data = form_extraction_and_compare(
        file, page_number_table, digit_to_part_mapping, custom_data, page_columns, page_pair_index)
    if custom_data['data']['mapping_results'] is not None:
        revalidated_results = revalidate_matches(
            image, custom_data['data']['mapping_results'], digit_to_part_mapping, threshold=0.9)
    custom_data['data']['mapping_results'] = revalidated_results
    # save_part_count(username, file, filename, custom_data['code'],custom_data['data']['mapping_results'],custom_data['data']['note'],custom_data['data']['error_pages'],custom_data['msg'])
    pdf.close()
    return custom_data


class PartCountHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file, filename, pdf_rect, page_number_explore, page_number_table, page_columns,
                      page_pair_index):
        return PartCountHandlerOCR(
            username, file, filename, pdf_rect, page_number_explore, page_number_table, page_columns, page_pair_index)

    async def post(self):
        username = self.current_user
        params = tornado.escape.json_decode(self.request.body)
        filename = params['filename']
        rect = params['rect']
        file = params['filePath']
        print(rect)
        # 使用列表切片获取除第一项之外的所有元素，并使用列表推导式将它们转换为整数
        # rect_int= [int(x) for x in rect[1:]]
        rect_int = [int(x) for x in rect]
        xmin = rect_int[0]
        ymin = rect_int[1]
        xmax = (rect_int[0] + rect_int[2])
        ymax = (rect_int[1] + rect_int[3])
        scale_factor = 72 / 300
        pdf_rect = [xmin * scale_factor, ymin * scale_factor,
                    xmax * scale_factor, ymax * scale_factor]
        print(pdf_rect)
        page_number_explore = int(params['page_explore'])
        page_number_table = int(params['page_table'])
        page_columns = int(params['columnCount'])
        page_pair_index = params['pair_index']
        print(page_columns, page_pair_index)
        custom_data = await self.process_async(
            username, file, filename, pdf_rect, page_number_explore, page_number_table, page_columns, page_pair_index)
        save_part_count(username['username'], file, custom_data['code'], custom_data['data'], custom_data['msg'])
        self.write(custom_data)
