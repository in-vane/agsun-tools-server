import os
import io
import re
import sys

import cv2
import fitz  # PyMuPDF
import pdfplumber
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


DPI = 600
ZOOM = DPI / 72


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
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

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

    return filtered_contours  # or return [largest_contour] if you want to only return the largest one


def save_modified_page_only(pdf_path, page_number, rect):
    """
    仅保存修改后的PDF页面到新文件中。

    :param pdf_path: 输入PDF文件的路径。
    :param output_path: 修改后PDF页面的保存路径。
    :param page_number: 要修改的页面编号（从0开始）。
    :param rect: 保留内容的矩形区域，格式为(x0, y0, x1, y1)。
    """
    doc = fitz.open(pdf_path)  # 打开PDF文件
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
    new_page = new_doc.new_page(-1, width=rect.width, height=rect.height)  # 添加一个新页面，大小与裁剪区域一致

    # 将裁剪区域的内容绘制到新页面上
    clip = rect  # 定义裁剪区域
    new_page.show_pdf_page(new_page.rect, doc, page_number, clip=clip)
    # 将新文档保存到字节流中
    output_stream = io.BytesIO()
    new_doc.save(output_stream)
    new_doc.close()
    doc.close()

    # 返回字节流中的数据
    return output_stream.getvalue()


def is_point_inside_bbox(point, bbox, margin=0):
    x, y = point
    xmin, ymin, xmax, ymax = bbox
    return (xmin - margin) <= x <= (xmax + margin) and (ymin - margin) <= y <= (ymax + margin)


def calculate_center(bbox):
    x_min, y_min, x_max, y_max = bbox
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    return (center_x, center_y)


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
    center_point = calculate_center(bbox)
    min_distance = np.inf
    closest_line = None
    margin = 10  # 定义边缘容忍范围为10个像素

    for line in lines:
        x1, y1, x2, y2 = line[0]  # 注意根据实际情况调整直线数据的解包方式
        line_endpoints = (x1, y1, x2, y2)

        # 检查两个端点是否在扩展的bbox内
        inside_first_with_margin = is_point_inside_bbox((x1, y1), bbox, margin)
        inside_second_with_margin = is_point_inside_bbox((x2, y2), bbox, margin)

        # 检查两个端点是否在原始bbox外
        outside_first_without_margin = not is_point_inside_bbox((x1, y1), bbox, -margin)
        outside_second_without_margin = not is_point_inside_bbox((x2, y2), bbox, -margin)

        # 如果两个端点都在边缘容忍范围外，或者一个在内一个在外
        if (outside_first_without_margin and outside_second_without_margin) or \
                (inside_first_with_margin != inside_second_with_margin):
            distance = point_to_line_distance(center_point, line_endpoints)
            if distance < min_distance:
                min_distance = distance
                closest_line = line_endpoints

    return closest_line


def get_image(pdf_path, page_number, crop_rect):
    output_pdf_bytes = save_modified_page_only(pdf_path, page_number - 1, crop_rect)
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
    image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    cv2.imwrite("D:/PycharmProjects/part_count/material/result1.png",image)
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
    return image, number_bboxes


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

def get_results(image, number_bboxes, image1):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 应用高斯模糊和Canny边缘检测
    blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    edges = cv2.Canny(blurred_image, 50, 150)
    # 使用霍夫变换检测直线
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=100, maxLineGap=25)
    line_image = image.copy()
    # 遍历检测到的每条线段
    for line in lines:
        x1, y1, x2, y2 = line[0]
        # 在line_image上绘制线段
        cv2.line(line_image, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.imwrite('D:/PycharmProjects/part_count/material/result3.png', line_image)

    filtered_contours = get_contour_image(image)
    contour_image = image.copy()
    cv2.drawContours(contour_image, filtered_contours, -1, (0, 255, 0), 3)
    cv2.imwrite('D:/PycharmProjects/part_count/material/result2.png', contour_image)
    # 初始化字典来存储数字和最近直线的配对关系
    digit_to_part_mapping = {}
    # 遍历每个识别到的数字
    for text, bbox in number_bboxes.items():
        x_min, y_min, x_max, y_max = [int(coord * ZOOM) for coord in bbox]
        bbox = [x_min, y_min, x_max, y_max]
        # 因为边框格式已经统一，所以我们可以直接使用这些坐标绘制矩形
        cv2.rectangle(image1, (int(x_min), int(y_min)), (int(x_max), int(y_max)), (0, 255, 0), 2)
        # 在边框上方显示识别的文本
        cv2.putText(image1, text, (int(x_min), int(y_min) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        # 寻找最近的直线
        closest_line = find_closest_line_to_bbox(bbox, lines)
        if closest_line:
            part_contour = extend_line_from_farthest_point(bbox, closest_line, filtered_contours)
            if part_contour is not None:
                digit_to_part_mapping[text] = {'part_contour': part_contour, 'bbox': bbox, 'similar_parts_count': 0}
                # 绘制最近的直线
                cv2.line(image1, (closest_line[0], closest_line[1]), (closest_line[2], closest_line[3]), (255, 0, 0),
                         2)
                # 绘制零件框
                cv2.drawContours(image1, [part_contour], -1, (0, 0, 255), 2)
            else:
                # 如果未找到零件框，则更新字典中的相应信息
                digit_to_part_mapping[text] = {'part_contour': None, 'bbox': bbox, 'similar_parts_count': 0}
    cv2.imwrite('D:/PycharmProjects/part_count/material/result4.png',image1)
    for digit, info in digit_to_part_mapping.items():
        if 'part_contour' in info and info['part_contour'] is not None:
            # template = extract_template_with_contour(image, info['part_contour'])
            # count = find_and_count_matches(image, template, threshold=0.9)
            count, matched_contours = find_and_count_matches(image, filtered_contours, info['part_contour'], threshold=0.02)
            digit_to_part_mapping[digit]['similar_parts_count'] = count
            # 在字典中存储匹配到的轮廓
            digit_to_part_mapping[digit]['matched_contours'] = matched_contours
    return digit_to_part_mapping


# 定义一个函数来检查序列是否递增
def is_increasing(sequence):
    return all(x < y for x, y in zip(sequence, sequence[1:]))


# 定义一个函数来检查字符串是否包含数字
def contains_number(s):
    return any(char.isdigit() for char in s)

def revalidate_matches(image, failed_matches, digit_to_part_mapping,threshold=1):
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
                    first_template_gray = cv2.cvtColor(first_template, cv2.COLOR_BGR2GRAY)
                    # 首先，确认first_template_gray是否需要增加边框

                    # 提取模板及其alpha通道作为掩码
                    template = extract_template_with_contour(image, digit_to_part_mapping[key]['part_contour'])
                    template_rgb = template[..., :3]
                    template_alpha = template[..., 3]
                    template_gray = cv2.cvtColor(template_rgb, cv2.COLOR_BGR2GRAY)
                    if first_template_gray.shape[0] < template_gray.shape[0] or first_template_gray.shape[1] < \
                            template_gray.shape[1]:
                        # 计算需要增加的高度和宽度
                        delta_height = max(template_gray.shape[0] - first_template_gray.shape[0] + padding, 0)
                        delta_width = max(template_gray.shape[1] - first_template_gray.shape[1] + padding, 0)

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
                if successful_matches_count == expected[0]:
                    match_success = True
                    revalidated_results.append((key, match_success, None, None))
                else:
                    match_success = False
                    revalidated_results.append((key, match_success, successful_matches_count, expected))
            else:
                # 如果没有匹配的轮廓，保留原来的匹配失败信息
                revalidated_results.append((key, False, found, expected))
        else:
            # 如果原本匹配成功，直接添加到结果中
            revalidated_results.append((key, matched, found, expected))

    return revalidated_results
def form_extraction_and_compare(pdf_path, page_number, digit_to_part_mapping):
    results = []  # 用于存储比对结果
    with pdfplumber.open(pdf_path) as pdf:
        # 确保页面号码在PDF文档范围内
        if page_number > len(pdf.pages) or page_number < 1:
            return 'Page number out of range', []

        page = pdf.pages[page_number]
        tables = page.extract_tables()

        # 如果页面上没有表格，返回错误信息
        if not tables:
            return 'No tables found on page {}'.format(page_number), []

        for table in tables:
            # 检查列数是否是3的倍数，如果是则按每3列分割处理
            num_columns = len(table[0])
            if num_columns % 3 == 0:
                # 处理每个子表格
                for i in range(0, num_columns, 3):
                    sub_table = [row[i:i + 3] for row in table]  # 获取子表格
                    df = pd.DataFrame(sub_table[1:], columns=sub_table[0])

                    if not contains_number(df.iloc[0, 0]):
                        df = df.iloc[1:]

                    try:
                        # df.iloc[:, 0] = pd.to_numeric(df.iloc[:, 0], errors='coerce').astype(int)
                        df[df.columns[0]] = pd.to_numeric(df.iloc[:, 0], errors='coerce').astype(int)
                        df = df.dropna(subset=[df.columns[0]])
                    except ValueError:
                        continue  # 无法转换第一列为整数，跳过此子表格

                    numbers = df.iloc[:, 0].tolist()
                    if is_increasing(numbers):
                        # 这里假设digit_to_part_mapping字典的key为字符串形式的数字
                        for key, value in digit_to_part_mapping.items():
                            # 查找第一列中值等于key的行
                            row = df[df.iloc[:, 0] == int(key)]
                            if not row.empty:
                                third_column_value = row.iloc[0, 2]  # 假设只有一行匹配
                                numbers_in_third_column = re.findall(r'\d+', third_column_value)
                                if numbers_in_third_column:
                                    numbers = [int(num) for num in numbers_in_third_column]
                                    if value['similar_parts_count'] in numbers:
                                        results.append((key, True, None, None))  # 匹配成功
                                    else:
                                        results.append(
                                            (key, False, value['similar_parts_count'], numbers))  # 匹配失败，返回详细信息
                                else:
                                    results.append((key, False, value['similar_parts_count'], []))  # 第三列没有找到数字，返回详细信息
    # 如果处理完所有表格后没有找到符合要求的表格，也返回错误信息
    if not results:
        return 'No matching tables found', []
    return 'Success', results


def check_part_count(filename, rect=[20, 60, 550, 680], page_number_explore=6, page_number_table=7):
    pdf_path = f"./python/assets/pdf/{filename}"
    crop_rect = fitz.Rect(rect[0], rect[1], rect[2], rect[3])  # 裁剪区域
    image, bbox = get_image(pdf_path, page_number_explore, crop_rect)
    image1 = image.copy()
    digit_to_part_mapping = get_results(image, bbox, image1)
    status_message, match_results = form_extraction_and_compare(pdf_path, page_number_table - 1, digit_to_part_mapping)
    revalidated_results = revalidate_matches(image, match_results, digit_to_part_mapping, threshold=0.9)
    # 检查状态信息，并按需处理匹配结果
    results = []
    if status_message == 'Success':
        # 遍历匹配结果
        for key, matched, found, expected in revalidated_results:
            results.append({
                "no": key,
                "state": matched,
                "found": found,
                "expected": expected
            })
            if matched:
                print(f"Key: {key}, Matched: {matched}") # 如果匹配成功，打印关键字和匹配状态
            else:
                print(f"Key: {key}, Matched: {matched}, Found: {found}, Expected in Table: {expected}") # 如果匹配不成功，打印关键字、匹配状态以及找到和预期的数值
    else:
        print(status_message) # 如果状态消息不是'Success'，则打印出状态消息
    return status_message, results
