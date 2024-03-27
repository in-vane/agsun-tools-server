import base64
import re
from io import BytesIO
import fitz  # PyMuPDF
import cv2
import numpy as np


def pdf_to_image(file, page_number=0, resolution=300):
    doc = fitz.open(stream=BytesIO(file))
    page = doc.load_page(page_number)

    # 获取页面文本
    text = page.get_text()
    # 使用正则表达式匹配数字 x 数字 mm 的字符串
    w = 0
    d = 0
    match = re.search(r'(\d+) x (\d+) mm', text)
    if match:
        # 提取匹配到的两个数字
        w = int(match.group(1))
        d = int(match.group(2))

    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1).prescale(resolution / 72, resolution / 72))
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n), w, d


def find_largest_rectangle_opencv(image, resolution=300):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

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
    largest_width_mm = (w * mm_per_inch) / resolution
    largest_height_mm = (h * mm_per_inch) / resolution

    return largest_width_mm, largest_height_mm, x, y, w, h


def compare_size(file):
    RESOLUTION = 300
    image, width, height = pdf_to_image(file, page_number=0, resolution=RESOLUTION)
    largest_width, largest_height, x, y, w, h = find_largest_rectangle_opencv(image, resolution=RESOLUTION)

    is_error = False
    msg = "尺寸一致"
    if abs(width - largest_width) > 1 or abs(height - largest_height) > 1:
        is_error = True
        largest_width = int(largest_width)
        largest_height = int(largest_height)
        msg = f"尺寸不一致: 标注为({height} x {width}), 检测结果为({largest_height} x {largest_width})"
    # 在图像上插入错误提示文字
    t = f"Marked ({height} x {width}), Real ({largest_height} x {largest_width})"
    cv2.putText(image, t, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (24, 31, 172), 2)

    # 保存带有错误提示的图像
    # cv2.imwrite("error_image.jpg", image)

    # 显示图像
    # cv2.imshow("Largest Rectangle", image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    _, image_buffer = cv2.imencode('.jpg', image)
    image_base64 = base64.b64encode(image_buffer).decode('utf-8')

    return is_error, msg, image_base64
