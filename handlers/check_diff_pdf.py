import cv2
import numpy as np
from skimage.metrics import structural_similarity
import base64
import os
import fitz
from config import BASE64_PNG
from utils import base642img, img2base64
import sys
from PIL import Image, ImageChops, ImageStat
from utils import base64_to_image, img2base64, image_to_base64
import time

sys.path.append("..")
from save_filesys_db import save_Diffpdf
CODE_SUCCESS = 0
CODE_ERROR = 1

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor



def pdf_page_to_image(pdf_path, page_number, zoom_x=3.0, zoom_y=3.0):
    ''' pdf转换为图片 '''
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)  # 从0开始索引
    mat = fitz.Matrix(zoom_x, zoom_y)  # 定义缩放因子以提高图像质量
    pix = page.get_pixmap(matrix=mat)
    img = cv2.imdecode(np.frombuffer(pix.tobytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    doc.close()
    return img

def draw_frame(base64_img, color):
    # 将 base64 编码转换为图像
    img_data = base64.b64decode(base64_img)
    img_array = np.frombuffer(img_data, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    # 确定框的颜色
    if color == 'red':
        frame_color = (0, 0, 255)  # 红色
    elif color == 'blue':
        frame_color = (255, 0, 0)  # 蓝色
    else:
        raise ValueError("color 参数必须是 'red' 或 'blue'")

    # 在图像上绘制一个框
    height, width, _ = img.shape
    cv2.rectangle(img, (0, 0), (width, height), frame_color, 20)  # 线宽为20

    # 将图像转换回 base64 编码
    _, buffer = cv2.imencode('.jpg', img)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"{BASE64_PNG}{image_base64}"

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

def compare_explore_no_resize(base64_data_old: str, base64_data_new: str):
    differece = False
    # img_[number]: base64
    before = base642img(base64_data_old)
    after = base642img(base64_data_new)

    # Convert images to grayscale
    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    # Compute SSIM between the two images
    try:
        (score, diff) = structural_similarity(before_gray, after_gray, full=True)
    except ValueError as e:
        print("不resize发生错误,则调整图片")
        # 调用备用函数并返回备用结果

        score, differece, image_base64, image2_base64 = compare_explore(base64_data_old, base64_data_new)
        return score, differece, image_base64, image2_base64
    if score < 0.95:
        print(f"不resize其相识度为{score}小于0.95,则调整图片")
        score, differece, image_base64, image2_base64 = compare_explore(base64_data_old, base64_data_new)
        return score, differece, image_base64, image2_base64
    diff = (diff * 255).astype("uint8")
    diff_box = cv2.merge([diff, diff, diff])

    # 调整后的阈值化代码
    threshold_value = 150  # 可以根据需要调整这个值
    thresh = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY_INV)[1]

    # 调整后的轮廓检测代码
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

            differece = True
    # 将掩膜应用到原图像上
    filled_before = cv2.addWeighted(before, 1.0, mask_before, 1, 0)
    filled_after = cv2.addWeighted(after, 1.0, mask_after, 1, 0)

    # 编码图像为Base64
    image_base64_before = img2base64(filled_before)
    image_base64_after = img2base64(filled_after)

    return score, differece, f"data:image/png;base64,{image_base64_before}", f"data:image/png;base64,{image_base64_after}"

def compare_explore(base64_data_old: str, base64_data_new: str):
    differece = False
    # 调整图像大小
    before, after = resize(base64_data_old, base64_data_new)

    # 将图像转换为灰度图像
    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    # 计算两幅图像之间的结构相似度（SSIM）
    (score, diff) = structural_similarity(before_gray, after_gray, full=True)
    diff = (diff * 255).astype("uint8")

    # 调整后的阈值化代码
    threshold_value = 150  # 可以根据需要调整这个值
    thresh = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY_INV)[1]

    # 调整后的轮廓检测代码
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

            differece = True


    # 将掩膜应用到原图像上
    filled_before = cv2.addWeighted(before, 1.0, mask_before, 1, 0)
    filled_after = cv2.addWeighted(after, 1.0, mask_after, 1, 0)

    # 编码图像为Base64
    image_base64_before = img2base64(filled_before)
    image_base64_after = img2base64(filled_after)

    return score, differece, f"data:image/png;base64,{image_base64_before}", f"data:image/png;base64,{image_base64_after}"

def check_diff_pdf(username, file1, file2, file1_name, file2_name,  start_1, end_1, start_2, end_2):
    mismatch_list = []
    base64_strings = []
    doc1 = fitz.open(file1)
    doc2 = fitz.open(file2)

    total_page1 = len(doc1)  # 取 pdf1 的页数作为标准
    total_page2 = len(doc2)  # 取 pdf1 的页数作为标准
    if end_1 > total_page1 or end_2 > total_page2 or start_1 > end_1 or start_2 > end_2 or (end_1 - start_1) != (end_2 - start_2):
        msg = '输入页号错误'
        return CODE_ERROR, [], [], msg, msg
    if start_1 != -1 and start_2 != -1:
        start_1 = start_1 - 1  # 从0开始索引，所以减1
        start_2 = start_2 - 1  # 同理

        # 确保对比范围相同
        length = min(end_1 - start_1, end_2 - start_2)

        for i in range(length):
            page_index1 = start_1 + i
            page_index2 = start_2 + i

            if page_index1 < len(doc2) and page_index2 < len(doc2):  # 确保两份文档都有对应的页
                img1 = pdf_page_to_image(file1, page_index1)
                img2 = pdf_page_to_image(file2, page_index2)

                base64_img1 = img2base64(img1)
                base64_img2 = img2base64(img2)
                print(f"第一份文档的{page_index1 + 1}页与第二份文档的{page_index2 + 1}页进行对比")
                score, difference, result_base64, result2_base64 = compare_explore_no_resize(base64_img1, base64_img2)
                print(f"结构化对比对比{score}")

                if difference:
                    mismatch_list.append(page_index1 + 1)
                    mismatch_list.append(page_index1 + 1)
                    mismatch_list.append(page_index1 + 1)
                    mismatch_list.append(page_index1 + 1)
                    base64_strings.append(result_base64)
                    base64_strings.append(result2_base64)
                    base64_strings.append(f"data:image/png;base64,{base64_img1}")
                    base64_strings.append(f"data:image/png;base64,{base64_img2}")
            # 当页号范围不匹配
            else:
                if page_index1 < len(doc2):
                    img1 = pdf_page_to_image(file1, page_index1)
                    base64_img1 = img2base64(img1)
                    result_base64 = draw_frame(base64_img1, 'red')
                    base64_strings.append(result_base64)
                    mismatch_list.append(page_index1 + 1)
                if page_index2 < len(doc2):
                    img2 = pdf_page_to_image(file2, page_index2)
                    base64_img2 = img2base64(img2)
                    result_base64 = draw_frame(base64_img2, 'blue')
                    base64_strings.append(result_base64)
                    mismatch_list.append(page_index2 + 1)
    else:
        print("对比开始")
        for i in range(total_page1):
            if i < len(doc2):  # 确保 pdf2 也有这一页
                img1 = pdf_page_to_image(file1, i)
                img2 = pdf_page_to_image(file2, i)

                base64_img1 = img2base64(img1)
                base64_img2 = img2base64(img2)
                print(f"第一份文档的{i + 1}页与第二份文档的{i + 1}页进行对比")
                score, difference, result_base64, result2_base64 = compare_explore_no_resize(base64_img1, base64_img2)
                print(f"结构化对比对比{score}")
                if difference:
                    mismatch_list.append(i + 1)
                    mismatch_list.append(i + 1)
                    mismatch_list.append(i + 1)
                    mismatch_list.append(i + 1)
                    base64_strings.append(result_base64)
                    base64_strings.append(result2_base64)
                    base64_strings.append(f"data:image/png;base64,{base64_img1}")
                    base64_strings.append(f"data:image/png;base64,{base64_img2}")
            else:
                img1 = pdf_page_to_image(file1, i)
                base64_img1 = img2base64(img1)
                result_base64 = draw_frame(base64_img1, 'red')  # 使用绘制红框的函数
                base64_strings.append(result_base64)
                mismatch_list.append(i + 1)
        # 处理 file2 有页而 file1 没有的情况
        for i in range(total_page1, len(doc2)):
            img2 = pdf_page_to_image(file2, i)
            base64_img2 = img2base64(img2)
            result_base64 = draw_frame(base64_img2, 'blue')  # 使用绘制蓝框的函数
            base64_strings.append(result_base64)
            mismatch_list.append(i + 1)
    doc1.close()
    doc2.close()
    print(mismatch_list)
    error_msg = f"{list(set(mismatch_list))}页有差异"
    if len(mismatch_list) == 0:
        error_msg = '没有差异'
    save_Diffpdf(username['username'], CODE_SUCCESS, file1, file2, mismatch_list, base64_strings, error_msg, '')
    return CODE_SUCCESS, mismatch_list, base64_strings, error_msg, ''


class FullPageHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file1, file2,file1_name, file2_name, start_1, end_1, start_2, end_2):
        return check_diff_pdf(username, file1, file2,file1_name, file2_name, start_1, end_1, start_2, end_2)
    async def post(self):
        username = self.current_user
        start = time.time()
        param = tornado.escape.json_decode(self.request.body)
        file_path_1 = param['file_path_1']
        file_path_2 = param['file_path_2']
        start_1 = int(param.get('start_1', -1))
        end_1 = int(param.get('end_1', -1))
        start_2 = int(param.get('start_2', -1))
        end_2 = int(param.get('end_2', -1))
        filename1 = os.path.basename(file_path_1)
        filename2 = os.path.basename(file_path_2)
        code, pages, imgs_base64, error_msg, msg = await self.process_async(username,
                                                                           file_path_1, file_path_2, filename1,
                                                                           filename2, start_1, end_1, start_2, end_2 )
        custom_data = {
            "code": code,
            "data": {
                'pages': pages,
                'imgs_base64': imgs_base64,
                'error_msg': error_msg
            },
            "msg": msg
        }
        end = time.time()
        print(f"接口总耗时{end-start}秒")
        self.write(custom_data)