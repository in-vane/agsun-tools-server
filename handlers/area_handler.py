import cv2
import numpy as np
import os
from skimage.metrics import structural_similarity
import fitz
import base64
from PIL import Image
from io import BytesIO

from save_filesys_db import save_area

from main import MainHandler, need_auth
from config import BASE64_PNG
from utils import base642img, img2base64

from tornado.concurrent import run_on_executor
import tornado

import sys
sys.path.append("..")

DPI = 300
CODE_SUCCESS = 0
CODE_ERROR = 1
Image_PATH = './assets/image'

def merge_images(base64_img1, base64_img2):
    # 移除"data:image/png;base64,"前缀并解码第一张图片
    img_data1 = base64.b64decode(base64_img1.split(",")[1])
    img1 = Image.open(BytesIO(img_data1))

    # 移除前缀并解码第二张图片
    img_data2 = base64.b64decode(base64_img2.split(",")[1])
    img2 = Image.open(BytesIO(img_data2))

    # 获取两张图片的尺寸
    width1, height1 = img1.size
    width2, height2 = img2.size

    # 新图片的宽度为两张图片宽度之和，高度为两张图片中的最大高度
    new_width = width1 + width2
    new_height = max(height1, height2)

    # 创建一个新的空白图片，用于合并
    new_img = Image.new('RGB', (new_width, new_height))

    # 将第一张图片粘贴到新图片上
    new_img.paste(img1, (0, 0))
    # 将第二张图片粘贴到新图片上，紧跟第一张图片之后
    new_img.paste(img2, (width1, 0))

    # 将合并后的图片转换为base64
    buffered = BytesIO()
    new_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue())
    img_base64_str = "data:image/png;base64," + img_base64.decode()

    # 返回合并后的图片的base64编码字符串
    return img_base64_str

def resize(base64_1, base64_2):
    image_A = base642img(base64_1)
    image_B = base642img(base64_2)
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

    # 确保描述符不为空
    if descriptors_A is None or descriptors_B is None:
        return image_A, image_B
        # raise ValueError("One of the descriptors is None, cannot perform matching.")

    # 转换描述符为浮点数
    descriptors_A = np.float32(descriptors_A)
    descriptors_B = np.float32(descriptors_B)

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
    if len(good_matches) < 4:
        return image_A, image_B
    # 提取匹配的关键点对的坐标
    src_pts = np.float32(
        [keypoints_B[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32(
        [keypoints_A[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    # 计算变换矩阵
    M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC)

    # 将图片 B 根据变换矩阵进行缩放和平移
    image_B_aligned = cv2.warpPerspective(
        image_B, M, (max_width, max_height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    # 如果 B 的尺寸发生了改变
    if image_B_aligned.shape[0] != max_height or image_B_aligned.shape[1] != max_width:
        # 如果小于最大尺寸，填补白色
        if image_B_aligned.shape[0] < max_height or image_B_aligned.shape[1] < max_width:
            padding_B_aligned = np.ones(
                (max_height, max_width, 3), dtype=np.uint8) * 255
            padding_B_aligned[:image_B_aligned.shape[0],
            :image_B_aligned.shape[1]] = image_B_aligned
            image_B_aligned = padding_B_aligned
        # 如果大于最大尺寸，裁减到最大尺寸
        elif image_B_aligned.shape[0] > max_height or image_B_aligned.shape[1] > max_width:
            image_B_aligned = image_B_aligned[:max_height, :max_width]

    return image_A, image_B_aligned

def compare_explore(username, filename1, file1, filename2, file2, base64_data_old: str, base64_data_new: str, mode):
    # img_[number]: base64
    before, after = resize(base64_data_old, base64_data_new)

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
    t = 100 if mode == 0 else 200
    thresh = cv2.threshold(diff, t, 255, cv2.THRESH_BINARY_INV)[1]
    contours = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[0] if len(contours) == 2 else contours[1]

    # 复制图像用于绘制差异
    filled_before = before.copy()
    filled_after = after.copy()

    # 创建一个掩膜图像，用于标记差异区域
    mask_before = np.zeros_like(filled_before)
    mask_after = np.zeros_like(filled_after)
    # 调整后的绘制差异区域代码
    for c in contours:
        area = cv2.contourArea(c)
        if area > 40:  # 只处理大于40的区域
            x, y, w, h = cv2.boundingRect(c)
            # 在掩膜上绘制深红色差异区域
            cv2.rectangle(mask_before, (x, y), (x + w, y + h), (0, 0, 139), -1)  # 深红色填充
            # 在掩膜上绘制深蓝色差异区域
            cv2.rectangle(mask_after, (x, y), (x + w, y + h), (255, 0, 0), -1)  # 蓝色填充

    # 将掩膜应用到原图像上
    filled_before = cv2.addWeighted(before, 1.0, mask_before, 1, 0)
    filled_after = cv2.addWeighted(after, 1.0, mask_after, 1, 0)

    # 编码图像为Base64
    image_base64_before = img2base64(filled_before)
    image_base64_after = img2base64(filled_after)
    image_base64 = merge_images(f"{BASE64_PNG}{image_base64_before}", f"{BASE64_PNG}{image_base64_after}")
    msg = ''
    save_area(username['username'], CODE_SUCCESS, file1, file2, f"{BASE64_PNG}{base64_data_old}", f"{BASE64_PNG}{base64_data_new}", image_base64, msg)
    return CODE_SUCCESS, image_base64, msg



class AreaHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, filename1, file1, filename2, file2, img_1, img_2, mode):
        return compare_explore(username, filename1, file1, filename2, file2, img_1, img_2, mode)


    @need_auth
    async def post(self):
        username = self.current_user
        params = tornado.escape.json_decode(self.request.body)
        file1 = params['file_path_1']
        filename1 = os.path.basename(file1)
        file2 = params['file_path_2']
        filename2 = os.path.basename(file2)
        img_1 = params['img_1']
        img_2 = params['img_2']
        mode = int(params.get('mode', 0))
        code, img_base64, msg = await self.process_async(username, filename1, file1, filename2, file2, img_1, img_2, mode)
        custom_data = {
            "result": img_base64
        }
        self.write(custom_data)
