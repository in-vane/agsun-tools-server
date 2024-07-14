

import re
import math
import os
import cv2
import fitz
import numpy as np

from main import MainHandler, need_auth
from config import BASE64_PNG
from utils import img2base64

from tornado.concurrent import run_on_executor

import tornado
from save_filesys_db import save_ce_size
import sys
sys.path.append("..")

CODE_SUCCESS = 0
CODE_ERROR = 1
MODE_RECT = 0  # 检测矩形
MODE_CIR = 1  # 检测圆形
MODE_MARK = 0  # 使用标注尺寸
MODE_USER = 1  # 使用用户输入尺寸
REG_SIZE = r'(\d+)\s*[xX\*]\s*(\d+)'
PIXELS_TO_MM = 25.4 / 600


def pdf_to_image(page, dpi=600):
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)

    return img


# 合并几乎重叠的线段
def merge_lines(lines, x_threshold=10, y_threshold=10):
    merged_lines = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        merged = False
        for i, (mx1, my1, mx2, my2) in enumerate(merged_lines):
            if (abs(x1 - mx1) < x_threshold and abs(y1 - my1) < y_threshold and
                    abs(x2 - mx2) < x_threshold and abs(y2 - my2) < y_threshold):
                merged_lines[i] = (min(x1, mx1), min(
                    y1, my1), max(x2, mx2), max(y2, my2))
                merged = True
                break
        if not merged:
            merged_lines.append((x1, y1, x2, y2))
    return merged_lines


def find_rect(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # res = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    res = cv2.equalizeHist(gray)
    # 应用边缘检测
    edges = cv2.Canny(res, 30, 150, apertureSize=3)

    # 使用霍夫变换检测线段
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50,
                            minLineLength=120, maxLineGap=20)
    merged_lines = merge_lines(lines, x_threshold=10, y_threshold=10)

    # 初始化变量以存储最左上角和最右下角的线段
    top_left_lines = [None, None]
    bottom_right_lines = [None, None]
    dist = np.sqrt(image.shape[1] ** 2 + image.shape[0] ** 2)
    min_dist_top_left = [dist, dist]
    min_dist_bottom_right = [dist, dist]

    if merged_lines is not None:
        for line in merged_lines:
            x1, y1, x2, y2 = line
            # 计算线段的中心点
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            # 计算到左上角的距离
            dist_top_left = np.sqrt(cx ** 2 + cy ** 2)
            if dist_top_left < min_dist_top_left[0]:
                min_dist_top_left[1] = min_dist_top_left[0]
                top_left_lines[1] = top_left_lines[0]
                min_dist_top_left[0] = dist_top_left
                top_left_lines[0] = line
            elif dist_top_left < min_dist_top_left[1]:
                min_dist_top_left[1] = dist_top_left
                top_left_lines[1] = line

            # 计算到右下角的距离
            dist_bottom_right = np.sqrt(
                (cx - image.shape[1]) ** 2 + (cy - image.shape[0]) ** 2)
            if dist_bottom_right < min_dist_bottom_right[0]:
                min_dist_bottom_right[1] = min_dist_bottom_right[0]
                bottom_right_lines[1] = bottom_right_lines[0]
                min_dist_bottom_right[0] = dist_bottom_right
                bottom_right_lines[0] = line
            elif dist_bottom_right < min_dist_bottom_right[1]:
                min_dist_bottom_right[1] = dist_bottom_right
                bottom_right_lines[1] = line

    # print(f"File: {file_num}")
    # print("⇱:", top_left_lines)
    # print("⇲:", bottom_right_lines)

    x_left, x_right = 0, float('inf')
    y_top, y_bottom = 0, float('inf')
    # 绘制检测到的线段
    for line in top_left_lines:
        if line is not None:
            x1, y1, x2, y2 = line
            x_left = max(x_left, x1, x2)
            y_top = max(y_top, y1, y2)
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

    for line in bottom_right_lines:
        if line is not None:
            x1, y1, x2, y2 = line
            x_right = min(x_right, x1, x2)
            y_bottom = min(y_bottom, y1, y2)
            cv2.line(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

    width = (x_right - x_left) * PIXELS_TO_MM
    height = (y_bottom - y_top) * PIXELS_TO_MM
    # print(f"x_left: {x_left}, x_right: {x_right}")
    # print(f"y_top: {y_top}, y_bottom: {y_bottom}")
    print(f"{width} x {height}")

    return round(width, 2), round(height, 2)


# 检测半径
def find_radius(img):
    '''获取最大矩形的尺寸'''
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # 转为灰度图
    # 使用Canny算法检测边缘
    edges = cv2.Canny(gray, 25, 150, apertureSize=3)
    # 寻找轮廓
    contours, _ = cv2.findContours(
        edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    max_area = 0
    largest_rectangle = None

    # 遍历轮廓并使用多边形逼近方法检查是否为长方形
    for cnt in contours:
        # 计算轮廓的近似形状
        epsilon = 0.05 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        # 如果轮廓是四边形，可能是长方形或正方形
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > max_area:
                max_area = area
                largest_rectangle = approx  # 更新最大面积长方形

    width_mm = 0
    height_mm = 0

    # 如果找到了最大长方形，绘制它
    if largest_rectangle is not None:
        # 在原图上绘制最大长方形
        cv2.drawContours(img, [largest_rectangle], 0, (0, 255, 0), 3)
        print("Largest rectangle detected!")

        # 计算长和宽
        p1, p2, p3, p4 = largest_rectangle.reshape(4, 2)
        side1 = np.linalg.norm(p1 - p2)
        side2 = np.linalg.norm(p2 - p3)
        # 转换像素到毫米
        width_mm = max(side1, side2) * PIXELS_TO_MM
        height_mm = min(side1, side2) * PIXELS_TO_MM

        print(f"The largest Width = {width_mm}, Height = {height_mm}")

    # 显示图像（用于测试）
    # cv2.imshow('Detected Largest Rectangle', img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    radius_mm = (width_mm + height_mm) * math.sqrt(2) / 2

    return round(radius_mm, 2)


def find_largest_size(sizes):
    '''找出最大的尺寸'''
    if not sizes:
        return 0, 0
    return max(sizes, key=lambda size: size[0] * size[1])  # 以面积为标准选择最大尺寸


def extract_size(page):
    '''获取标注尺寸'''
    text = page.get_text()
    w = 0
    h = 0
    matches = re.findall(REG_SIZE, text)
    sizes = []
    for match in matches:
        w = int(match[0])
        h = int(match[1])
        sizes.append((w, h))
    largest_size = find_largest_size(sizes)
    r = sum(largest_size) * math.sqrt(2) / 2

    return largest_size[0], largest_size[1], r


def compare(a, b):
    return abs(a - b) > 1


def check_size(username, filename, file, options, params):
    doc = fitz.open(file)
    page = doc.load_page(0)

    if options["active"] == MODE_MARK:
        w_1, h_1, r_1 = extract_size(page)
    if options["active"] == MODE_USER:
        w_1, h_1, r_1 = params['width'], params['height'], params['radius']

    # 主逻辑
    is_error = False
    err_msg = ""

    img = pdf_to_image(page)

    if options["mode"] == MODE_RECT:
        w_2, h_2 = find_rect(img)
        print(abs(w_1 - w_2), abs(h_1 - h_2))
        if abs(w_1 - w_2) > 1 or abs(h_1 - h_2) > 1:
            is_error = True
        err_msg = f"标注为({w_1} x {h_1}), 检测结果为({w_2} x {h_2})"
    if options["mode"] == MODE_CIR:
        r_2 = find_radius(img)
        if abs(r_1 - r_2) > 1:
            is_error = True
        err_msg = f"标注为({r_1}), 检测结果为({r_2})"

    print(is_error)
    message = f"尺寸不一致, {err_msg}" if is_error else '尺寸一致'
    print(message)
    img_base64 = img2base64(img)
    img_base64 = f"{BASE64_PNG}{img_base64}"
    save_ce_size(username['username'], CODE_SUCCESS,
                 file, is_error, message, img_base64, '')
    doc.close()

    return CODE_SUCCESS, is_error, message, img_base64, ''


class SizeHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, filename, body, options, params):
        return check_size(username, filename, body, options, params)

    @need_auth
    async def post(self):
        username = self.current_user
        param = tornado.escape.json_decode(self.request.body)
        file = param['filePath']
        filename = os.path.basename(file)
        mode = int(param.get('mode', 0))
        active = int(param.get('active', 0))
        width = int(param.get('width', -1))
        height = int(param.get('height', -1))
        radius = int(param.get('radius', -1))

        options = {
            "mode": mode,
            "active": active,
        }
        params = {
            "width": width,
            "height": height,
            "radius": radius,
        }

        code, error, message, img_base64, msg = await self.process_async(username, filename, file, options, params)
        custom_data = {
            "code": code,
            "data": {
                "error": error,
                "img_base64": img_base64,
                "message": message
            },
            "msg": msg,
        }
        self.write(custom_data)
