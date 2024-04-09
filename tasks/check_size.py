from config import BASE64_PNG
import re
import base64
from io import BytesIO
import cv2
import fitz
import numpy as np

import sys
sys.path.append('..')


RESOLUTION = 300
REG_SIZE = [r'(\d+) x (\d+)', r'(\d+)x(\d+)', r'(\d+)X(\d+)', r'(\d+)\*(\d+)']


def pdf_to_image(file, page_number=0,):
    doc = fitz.open(stream=BytesIO(file))
    page = doc.load_page(page_number)
    text = page.get_text()
    w = 0
    h = 0
    match = re.search(r'(\d+)x(\d+)', text)
    if match:
        w = int(match.group(1))
        h = int(match.group(2))

    pix = page.get_pixmap(matrix=fitz.Matrix(
        1, 1).prescale(RESOLUTION / 72, RESOLUTION / 72))
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n), w, h


def find_largest_rectangle_opencv(image,):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(
        edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    largest_area = 0
    largest_contour = None

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > largest_area:
            largest_area = area
            largest_contour = contour

    x, y, w, h = cv2.boundingRect(largest_contour)

    # 在图像上绘制蓝色矩形边框
    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # 转换为毫米
    mm_per_inch = 25.4
    largest_width_mm = (w * mm_per_inch) / RESOLUTION
    largest_height_mm = (h * mm_per_inch) / RESOLUTION

    return largest_width_mm, largest_height_mm, x, y


def compare_size(file):
    image, width, height = pdf_to_image(file, page_number=0)
    largest_width, largest_height, x, y = find_largest_rectangle_opencv(image)
    largest_width, largest_height = int(largest_width), int(largest_height)

    is_error = False
    message = "尺寸一致"

    if abs(width - largest_width) > 1 or abs(height - largest_height) > 1:
        is_error = True
        message = f"尺寸不一致: 标注为({width} x {height}), 检测结果为({largest_width} x {largest_height})"
    # 在图像上插入错误提示文字
    t = f"Marked ({width} x {height}), Real ({largest_width} x {largest_height})"
    cv2.putText(image, t, (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (24, 31, 172), 2)

    # 保存带有错误提示的图像
    # cv2.imwrite("error_image.jpg", image)

    _, image_buffer = cv2.imencode('.jpg', image)
    image_base64 = base64.b64encode(image_buffer).decode('utf-8')

    return is_error, message, f"{BASE64_PNG}{image_base64}"
