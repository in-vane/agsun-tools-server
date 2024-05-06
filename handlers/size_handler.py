
import io
import re
import math

import cv2
import fitz
import numpy as np

from main import MainHandler, need_auth
from config import BASE64_PNG
from utils import img2base64

from tornado.concurrent import run_on_executor

from save_filesys_db import save_CEsize
import sys
sys.path.append("..")

CODE_SUCCESS = 0
CODE_ERROR = 1
MODE_RECT = 0  # 检测矩形
MODE_CIR = 1  # 检测圆形
MODE_MARK = 0  # 使用标注尺寸
MODE_USER = 1  # 使用用户输入尺寸
REG_SIZE = r'(\d+)\s*[xX\*]\s*(\d+)'


def pdf_to_image(page, dpi=600):
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)

    return img


# 检测矩形
def find_rectangles(img):
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
        pixels_to_mm = 25.4 / 600
        width_mm = max(side1, side2) * pixels_to_mm
        height_mm = min(side1, side2) * pixels_to_mm

        print(f"The largest Width = {width_mm}, Height = {height_mm}")

    # 显示图像（用于测试）
    # cv2.imshow('Detected Largest Rectangle', img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    radius_mm = (width_mm + height_mm) * math.sqrt(2) / 2

    return width_mm, height_mm, radius_mm


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
    doc = fitz.open(stream=(io.BytesIO(file)))
    page = doc.load_page(0)

    if options["active"] == MODE_MARK:
        w_1, h_1, r_1 = extract_size(page)
    if options["active"] == MODE_USER:
        w_1, h_1, r_1 = params['width'], params['height'], params['radius']

    # 主逻辑
    img = pdf_to_image(page)
    w_2, h_2, r_2 = find_rectangles(img)

    is_error = False
    err_msg = ""
    if options["mode"] == MODE_RECT:
        if abs(w_1 - w_2) > 1 or abs(h_1 - h_2) > 1:
            is_error = True
        err_msg = f"标注为({w_1} x {h_1}), 检测结果为({w_2} x {h_2})"
    if options["mode"] == MODE_CIR:
        if abs(r_1 - r_2) > 1:
            is_error = True
        err_msg = f"标注为({r_1}), 检测结果为({r_2})"
    message = f"尺寸不一致, {err_msg}" if is_error else '尺寸一致'

    img_base64 = img2base64(img)
    img_base64 = f"{BASE64_PNG}{img_base64}"
    save_CEsize(username, doc, filename, CODE_SUCCESS, is_error, message, img_base64, '')
    doc.close()

    return CODE_SUCCESS, is_error, message, img_base64, ''


class SizeHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, filename, body, options, params):
        return check_size(username, filename, body, options, params)

    @need_auth
    async def post(self):
        username = self.current_user
        files = self.get_files()
        filename, body = files[0]["filename"], files[0]["body"]
        mode = int(self.get_argument('mode', default=0))
        active = int(self.get_argument('active', default=0))
        width = int(self.get_argument('width', default=-1))
        height = int(self.get_argument('height', default=-1))
        radius = int(self.get_argument('radius', default=-1))

        options = {
            "mode": mode,
            "active": active,
        }
        params = {
            "width": width,
            "height": height,
            "radius": radius,
        }

        code, error, message, img_base64, msg = await self.process_async(username, filename, body, options, params)
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
