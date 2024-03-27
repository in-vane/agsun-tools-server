import os
import sys
import base64
from io import BytesIO

import cv2
import fitz
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity

from .utils import pdf2img


# 常量
DPI = 300
BASE64_PNG = 'data:image/png;base64,'
MODE_NORMAL = 0
MODE_VECTOR = 1


# 判断页面是否是矢量图
def is_vector_page(page):
    # 获取页面中的矢量元素数量
    vector_count = len(page.get_drawings())
    print(vector_count)
    # 判断矢量元素数量是否超过阈值
    return vector_count > 1000


def img2base64(img):
    _, image_buffer = cv2.imencode('.jpg', img)
    image_base64 = base64.b64encode(image_buffer).decode('utf-8')
    return image_base64


async def pdf2img_single(ws, pdf_path, options):
    doc = fitz.open(pdf_path)
    total = len(doc)
    if 'limit' in options:
        total = min(total, options['limit'])

    for page_number in range(total):
        page = doc.load_page(page_number)
        img_base64 = ''

        if(options['mode'] == MODE_NORMAL):
            img_base64 = pdf2img(page, dpi=72)
        if(options['mode'] == MODE_VECTOR):
            if is_vector_page(page):
                img_base64 = pdf2img(page, dpi=300)

        img_base64 = "" if not img_base64 else f"{BASE64_PNG}{img_base64}"
        await ws.write_message({
            "total": total,
            "current": page_number + 1,
            "img_base64": img_base64,
            "options": options
        })

    print('===== done =====')
    doc.close()


def resize(base64_1, base64_2):
    # 解码 base64 字符串为图像数据
    image_data_1 = base64.b64decode(base64_1)
    image_data_2 = base64.b64decode(base64_2)

    # 将图像数据转换为 numpy 数组
    nparr_1 = np.frombuffer(image_data_1, np.uint8)
    nparr_2 = np.frombuffer(image_data_2, np.uint8)

    # 读取图片 A 和 B
    image_A = cv2.imdecode(nparr_1, cv2.IMREAD_COLOR)
    image_B = cv2.imdecode(nparr_2, cv2.IMREAD_COLOR)

    # 计算最大尺寸
    max_height = max(image_A.shape[0], image_B.shape[0])
    max_width = max(image_A.shape[1], image_B.shape[1])

    # 如果尺寸小于最大尺寸，用白色填充
    if image_A.shape[0] < max_height or image_A.shape[1] < max_width:
        padding_A = np.ones((max_height, max_width, 3), dtype=np.uint8) * 255
        padding_A[:image_A.shape[0], :image_A.shape[1]] = image_A
        image_A = padding_A

    if image_B.shape[0] < max_height or image_B.shape[1] < max_width:
        padding_B = np.ones((max_height, max_width, 3), dtype=np.uint8) * 255
        padding_B[:image_B.shape[0], :image_B.shape[1]] = image_B
        image_B = padding_B

    # 初始化 SIFT 检测器
    sift = cv2.SIFT_create()

    # 在图片 A 和 B 上检测关键点和描述符
    keypoints_A, descriptors_A = sift.detectAndCompute(image_A, None)
    keypoints_B, descriptors_B = sift.detectAndCompute(image_B, None)

    # 使用 FLANN 匹配器进行特征匹配
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(descriptors_B, descriptors_A, k=2)

    # 寻找最佳匹配点对
    good_matches = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:
            good_matches.append(m)

    # 提取匹配的关键点对的坐标
    src_pts = np.float32([keypoints_B[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([keypoints_A[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    # 计算变换矩阵
    M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC)

    # 将图片 B 根据变换矩阵进行缩放和平移
    image_B_aligned = cv2.warpPerspective(image_B, M, (max_width, max_height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    # 如果 B 的尺寸发生了改变
    if image_B_aligned.shape[0] != max_height or image_B_aligned.shape[1] != max_width:
        # 如果小于最大尺寸，填补白色
        if image_B_aligned.shape[0] < max_height or image_B_aligned.shape[1] < max_width:
            padding_B_aligned = np.ones((max_height, max_width, 3), dtype=np.uint8) * 255
            padding_B_aligned[:image_B_aligned.shape[0], :image_B_aligned.shape[1]] = image_B_aligned
            image_B_aligned = padding_B_aligned
        # 如果大于最大尺寸，裁减到最大尺寸
        elif image_B_aligned.shape[0] > max_height or image_B_aligned.shape[1] > max_width:
            image_B_aligned = image_B_aligned[:max_height, :max_width]

    return image_A, image_B_aligned


def compare_explore(img_1, img_2):
    # img_[number]: base64
    before, after = resize(img_1, img_2)

    # Convert images to grayscale
    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    # Compute SSIM between the two images
    (score, diff) = structural_similarity(before_gray, after_gray, full=True)
    print("Image Similarity: {:.4f}%".format(score * 100))

    # The diff image contains the actual image differences between the two images
    # and is represented as a floating point data type in the range [0,1] 
    # so we must convert the array to 8-bit unsigned integers in the range
    # [0,255] before we can use it with OpenCV
    diff = (diff * 255).astype("uint8")
    diff_box = cv2.merge([diff, diff, diff])

    # Threshold the difference image, followed by finding contours to
    # obtain the regions of the two input images that differ
    thresh = cv2.threshold(diff, 5, 255, cv2.THRESH_BINARY_INV)[1]
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]

    # mask = np.zeros(before.shape, dtype='uint8')
    filled_after = after.copy()

    for c in contours:
        area = cv2.contourArea(c)
        if area > 40:
            x,y,w,h = cv2.boundingRect(c)
            # cv2.rectangle(before, (x, y), (x + w, y + h), (243,71,24), 2)
            # cv2.rectangle(after, (x, y), (x + w, y + h), (243,71,24), 2)
            cv2.rectangle(diff_box, (x, y), (x + w, y + h), (24, 31, 172), 2)
            # cv2.drawContours(mask, [c], 0, (255,255,255), -1)
            cv2.drawContours(filled_after, [c], 0, (24, 31, 172), -1)

    # cv2.imshow('before', before)
    # cv2.imshow('after', after)
    # cv2.imshow('diff', diff)
    # cv2.imshow('diff_box', diff_box)
    # cv2.imshow('mask', mask)
    # cv2.imshow('filled after', filled_after)
    # cv2.waitKey()

    # 图片转base64
    image_base64 = img2base64(filled_after)

    return image_base64