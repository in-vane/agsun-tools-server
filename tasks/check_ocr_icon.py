import base64
import cv2
import fitz
import numpy as np


DPI = 300
BASE64_JPG = 'data:image/jpeg;base64,'


def detect_and_filter_contours(img1, area_threshold=200):
    # 假设 img1 是你要处理的图像
    if len(img1.shape) == 2 or img1.shape[2] == 1:
        # img1 是灰度图像，不需要转换
        gray = img1
    else:
        # img1 是彩色图像，需要转换
        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    # Apply Gaussian blur
    blurred_image = cv2.GaussianBlur(gray, (5, 5), 0)
    # 使用Canny边缘检测
    edges = cv2.Canny(blurred_image, 100, 200)
    # 查找轮廓
    contours, _ = cv2.findContours(
        edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 过滤轮廓
    large_contours = [
        cnt for cnt in contours if cv2.contourArea(cnt) > area_threshold]
    return large_contours


def match_and_align_images(img1, img2):
    # # 二值化处理
    # _, img1_binary = cv2.threshold(img1, 127, 255, cv2.THRESH_BINARY)
    # _, img2_binary = cv2.threshold(img2, 127, 255, cv2.THRESH_BINARY)
    # 转换为灰度图
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    # 初始化SIFT检测器
    sift = cv2.SIFT_create()
    shape0, shape1 = img2.shape[0], img2.shape[1]

    # 检测关键点和描述符
    keypoints1, descriptors1 = sift.detectAndCompute(gray1, None)
    keypoints2, descriptors2 = sift.detectAndCompute(gray2, None)
    # 创建BF匹配器
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)
    # 应用比率测试
    good_matches = [m for m, n in matches if m.distance < 0.75 * n.distance]
    if len(good_matches) >= 4:
        pts_src = np.float32(
            [keypoints1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        pts_dst = np.float32(
            [keypoints2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        M, _ = cv2.findHomography(pts_src, pts_dst, cv2.RANSAC, 5.0)
        if M is not None:
            result = cv2.warpPerspective(img1, M, (shape1, shape0))
            before_gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            after_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            custom_data = {
                "error": True,
                "result": [before_gray, after_gray],
            }
        else:
            custom_data = {
                "error": False,
                "result": ["无法计算单应性矩阵"],
            }
    else:
        custom_data = {
            "error": False,
            "result": ["不足以计算单应性矩阵，匹配点过少。"],
        }

    return custom_data


def pyr_down_image(image, levels=1):
    """
    使用高斯金字塔对图像进行下采样
    :param image: 原始图像
    :param levels: 下采样的层数
    :return: 下采样后的图像
    """
    img_pyr = image.copy()
    for _ in range(levels):
        img_pyr = cv2.pyrDown(img_pyr)
    return img_pyr


def compare_contours(img1, img2):
    # # 转换为灰度图
    # gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    # gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # 应用Canny边缘检测
    edges1 = cv2.Canny(img1, 100, 200)
    edges2 = cv2.Canny(img2, 100, 200)

    # 比较边缘图
    diff = cv2.absdiff(edges1, edges2)

    # 可选：将差异显著化
    _, diff = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)

    return diff
# def highlight_unmatched_contours_aligned(img1_aligned, img2, large_contours1, large_contours2,
#                                          similarity_threshold=5):
#     # 初始化匹配状态列表，假设所有轮廓最开始都是未匹配的
#     matched1 = [False] * len(large_contours1)
#     matched2 = [False] * len(large_contours2)
#     # 对齐后的图片上的每个大轮廓，尝试找到第二张图片中的匹配轮廓
#     for i, contour1 in enumerate(large_contours1):
#         for j, contour2 in enumerate(large_contours2):
#             similarity = cv2.matchShapes(contour1, contour2, 1, 0.0)


def highlight_unmatched_contours(img1, img2, large_contours1, large_contours2, similarity_threshold=5, iou_threshold=0.1):
    # 假设所有轮廓最开始都是未匹配的
    matched1 = [False] * len(large_contours1)
    matched2 = [False] * len(large_contours2)

    # 存储每个img1轮廓的最佳匹配img2轮廓的索引和相应的最小相似度值
    best_matches = [(-1, float('inf'))] * len(large_contours1)
    img_shape = img1.shape[:2]  # 假设img1和img2的形状相同
    # 初始化img2中的轮廓匹配状态列表
    matched_in_img2 = [False] * len(large_contours2)

    # 尝试找到img2中与img1每个轮廓的最佳匹配
    for i, contour1 in enumerate(large_contours1):
        for j, contour2 in enumerate(large_contours2):
            if matched_in_img2[j]:
                continue  # 如果img2中的轮廓已匹配，则跳过
            similarity = cv2.matchShapes(contour1, contour2, 1, 0.0)
            if similarity < best_matches[i][1]:
                if best_matches[i][0] != -1:  # 如果之前有匹配，将旧匹配标记为未匹配
                    matched_in_img2[best_matches[i][0]] = False
                best_matches[i] = (j, similarity)
                matched_in_img2[j] = True  # 标记新匹配

    # 根据最佳匹配和相似度阈值更新匹配状态
    for i, (best_match_idx, best_similarity) in enumerate(best_matches):
        if best_similarity < similarity_threshold:
            matched1[i] = True
            if best_match_idx != -1:
                matched2[best_match_idx] = True

    # 高亮显示未匹配的轮廓
    for i, contour in enumerate(large_contours1):
        if not matched1[i]:  # 如果img1中的轮廓未匹配
            cv2.drawContours(img1, [contour], -1,
                             (0, 0, 255), 3)  # 在img1上用红色高亮显示

    for j, contour in enumerate(large_contours2):
        if not matched2[j]:  # 如果img2中的轮廓未匹配
            cv2.drawContours(img2, [contour], -1,
                             (255, 0, 0), 3)  # 在img2上用蓝色高亮显示

    return img1, img2


def check_ocr_icon(filename, img1, page_num):
    pdf_path = f"./assets/pdf/{filename}"
    # 解码 base64 字符串为图像数据
    image_data_1 = base64.b64decode(img1.split(',')[-1])
    nparr_1 = np.frombuffer(image_data_1, np.uint8)
    img1 = cv2.imdecode(nparr_1, cv2.IMREAD_COLOR)
    img1 = cv2.cvtColor(img1, cv2.COLOR_RGB2BGR)
    # 打开PDF文件
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num - 1)
    image = page.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72))
    img_array = np.frombuffer(image.samples, dtype=np.uint8).reshape(
        (image.height, image.width, 3))
    doc.close()
    img2 = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    custom_data = match_and_align_images(img1, img2)
    if custom_data['error']:
        large_contours1 = detect_and_filter_contours(custom_data['result'][0])
        large_contours2 = detect_and_filter_contours(custom_data['result'][1])
        img1_aligned_highlighted, img2_highlighted = highlight_unmatched_contours(cv2.cvtColor(
            custom_data['result'][0], cv2.COLOR_GRAY2BGR), cv2.cvtColor(custom_data['result'][1], cv2.COLOR_GRAY2BGR), large_contours1, large_contours2)
        cv2.imwrite(
            'D:/PycharmProjects/part_count/material/result1.png', img1_aligned_highlighted)
        cv2.imwrite(
            'D:/PycharmProjects/part_count/material/result2.png', img2_highlighted)
        _, image_buffer = cv2.imencode('.jpeg', img1_aligned_highlighted)
        image_base64_1 = base64.b64encode(image_buffer).decode('utf-8')
        _, image_buffer = cv2.imencode('.jpeg', img2_highlighted)
        image_base64_2 = base64.b64encode(image_buffer).decode('utf-8')
        custom_data['result'][0] = f"{BASE64_JPG}{image_base64_1}"
        custom_data['result'][1] = f"{BASE64_JPG}{image_base64_2}"
        return custom_data
    else:
        return custom_data
