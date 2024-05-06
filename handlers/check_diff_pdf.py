import cv2
import numpy as np
from skimage.metrics import structural_similarity
import base64
import os
import fitz
from config import BASE64_PNG
from utils import base642img, img2base64

CODE_SUCCESS = 0
CODE_ERROR = 1

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor



def resize(base64_1, base64_2):
    image_A = base642img(base64_1)
    image_B = base642img(base64_2)

    # 计算最大尺寸
    max_height = max(image_A.shape[0], image_B.shape[0])
    max_width = max(image_A.shape[1], image_B.shape[1])

    # 统一尺寸调整
    image_A = cv2.resize(image_A, (max_width, max_height), interpolation=cv2.INTER_AREA)
    image_B = cv2.resize(image_B, (max_width, max_height), interpolation=cv2.INTER_AREA)

    # 初始化 SIFT 检测器
    sift = cv2.SIFT_create()

    # 检测关键点和描述符
    keypoints_A, descriptors_A = sift.detectAndCompute(image_A, None)
    keypoints_B, descriptors_B = sift.detectAndCompute(image_B, None)

    # 确保描述符非空
    if descriptors_A is None or descriptors_B is None:
        return image_A, image_B

    # 描述符转换为 float32
    descriptors_A = descriptors_A.astype(np.float32)
    descriptors_B = descriptors_B.astype(np.float32)

    # FLANN 匹配器
    flann = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 5}, {'checks': 50})
    matches = flann.knnMatch(descriptors_B, descriptors_A, k=2)

    # Lowe's ratio test
    good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]

    # 至少需要4个好的匹配点进行变换
    if len(good_matches) >= 4:
        src_pts = np.float32([keypoints_B[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([keypoints_A[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        image_B_aligned = cv2.warpPerspective(image_B, M, (max_width, max_height))
        return image_A, image_B_aligned
    else:
        return image_A, image_B  # 未找到足够匹配时返回原始图像

    return image_A, image_B


def compare_explore(base64_data_old: str, base64_data_new: str):
    difference = False
    # # 从 base64 数据解码得到的图像进行大小调整
    # before, after = resize(base64_data_old, base64_data_new)
    #
    # # 将图像转换为灰度图
    # before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    # after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
    # 从 base64 数据解码得到的图像
    before = base642img(base64_data_old)
    after = base642img(base64_data_new)

    # 判断两张图片的尺寸是否相同
    if before.shape != after.shape:
        # 如果尺寸不同，调用 resize 方法进行调整
        before, after = resize(base64_data_old, base64_data_new)

    # 将图像转换为灰度图
    before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    # SSIM方法
    # (score, diff) = structural_similarity(before_gray, after_gray, full=True)
    # print("Image Similarity: {:.4f}%".format(score * 100))
    # # diff 图像包含两幅图像之间的实际差异
    # # 差异图像以浮点数据类型表示在 [0,1] 范围内
    # # 因此我们必须将数组转换为范围在 [0,255] 的8位无符号整数，才能使用 OpenCV
    # diff = (diff * 255).astype("uint8")
    # diff_box = cv2.merge([diff, diff, diff])
    #
    # # 对差异图像进行阈值处理，然后找到轮廓来
    # # 获取两个输入图像中差异的区域
    # thresh = cv2.threshold(diff, 150, 255, cv2.THRESH_BINARY_INV)[1]
    # contours = cv2.findContours(
    #     thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # contours = contours[0] if len(contours) == 2 else contours[1]
    # # 在修改后的图像上绘制差异
    # filled_after = after.copy()
    # 计算差异并找到差异区域

    # for c in contours:
    #     area = cv2.contourArea(c)
    #     if area > 40:
    #         x, y, w, h = cv2.boundingRect(c)
    #         cv2.rectangle(diff_box, (x, y), (x + w, y + h), (24, 31, 172), 2)
    #         cv2.drawContours(filled_after, [c], 0, (24, 31, 172), -1)
    #         difference = True
    # # 在修改后的图像上绘制差异
    # image_base64 = img2base64(filled_after)
    # 在 img2 上标注差异区域

    # cv2.absdiff方法
    diff = cv2.absdiff(before_gray, after_gray)
    _, thresh = cv2.threshold(diff, 200, 255, cv2.THRESH_BINARY)  # 阈值可以调整以获得最佳结果
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:  # 如果存在差异
        difference = True
    color_img1 = cv2.cvtColor(before_gray, cv2.COLOR_GRAY2BGR)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(color_img1, (x, y), (x + w, y + h), (0, 255, 0), 2)
    image_base64 = img2base64(color_img1)

    return f"{BASE64_PNG}{image_base64}", difference


def draw_red_frame(base64_img):
    # 将 base64 编码转换为图像
    img_data = base64.b64decode(base64_img)
    img_array = np.frombuffer(img_data, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    # 在图像上绘制一个红色的框
    height, width, _ = img.shape
    cv2.rectangle(img, (0, 0), (width, height), (0, 0, 255), 10)  # 红色框, 线宽为20

    # 将图像转换回 base64 编码
    _, buffer = cv2.imencode('.jpg', img)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"{BASE64_PNG}{image_base64}"


def pdf_page_to_image(pdf_path, page_number):
    ''' pdf转换为图片 '''
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)  # 从 0 开始索引
    pix = page.get_pixmap()
    img = cv2.imdecode(np.frombuffer(pix.tobytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    doc.close()
    return img

def process_mismatch_lists(mismatch_list, base64_strings, threshold=10):
    new_mismatch_list = []
    new_base64_strings = []
    continuous = ""

    i = 0
    while i < len(mismatch_list):
        start = mismatch_list[i]
        end = start
        count = 1

        # 寻找连续序列
        while i < len(mismatch_list) - 1 and mismatch_list[i + 1] == mismatch_list[i] + 1:
            end = mismatch_list[i + 1]
            i += 1
            count += 1

        if count >= threshold:  # 如果连续页数超过阈值
            new_mismatch_list.extend([start, end])
            new_base64_strings.extend([base64_strings[i - count + 1], base64_strings[i]])
            continuous += f"从第{start}页到第{end}页，两个文件格式变化巨大。"
        else:
            # 添加非连续或短连续区段的所有页
            new_mismatch_list.extend(mismatch_list[i - count + 1: i + 1])
            new_base64_strings.extend(base64_strings[i - count + 1: i + 1])

        i += 1

    return new_mismatch_list, new_base64_strings, continuous



def check_diff_pdf(username, file1, file2,file1_name, file2_name, page_num1, page_num2):
    mismatch_list = []
    base64_strings = []
    doc1 = fitz.open(file1)
    doc2 = fitz.open(file2)

    total_page1 = len(doc1)  # 取 pdf1 的页数作为标准
    total_page2 = len(doc2)  # 取 pdf1 的页数作为标准
    if page_num1 > total_page1 or page_num2 > total_page2:
        msg = '你输入的范围大于pdf的页号'
        return CODE_ERROR, [], [], '', msg
    if page_num1 != -1 and page_num2 != -1:
        for i in range(page_num1, total_page1):
            page_num1  = page_num1 - 1  # 从0开始索引，所以减1
            page_num2= page_num2 - 1  # 同理
            page_index2 = i + (page_num2 - page_num1)  # 计算 pdf2 的对应页码
            if page_index2 < len(doc2):  # 确保 pdf2 有对应的页
                img1 = pdf_page_to_image(file1, i)
                img2 = pdf_page_to_image(file2, page_index2)

                base64_img1 = img2base64(img1)
                base64_img2 = img2base64(img2)

                result_base64, difference = compare_explore(base64_img1, base64_img2)
                if difference:
                    mismatch_list.append(i + 1)
                    base64_strings.append(result_base64)
                # output_path = os.path.join(output_dir, f"{i + 1}.jpg")
                # base64_to_image(result_base64, output_path)
            else:
                result_base64 = draw_red_frame(base64_img1)  # 使用绘制红框的函数
                base64_strings.append(result_base64)
                # output_path = os.path.join(output_dir, f"{i + 1}.jpg")
                # base64_to_image(result_base64, output_path)
                mismatch_list.append(i + 1)
        continuous = ''
    else:
        print("对比开始")
        for i in range(total_page1):
            if i < len(doc2):  # 确保 pdf2 也有这一页
                img1 = pdf_page_to_image(file1, i)
                img2 = pdf_page_to_image(file2, i)

                base64_img1 = img2base64(img1)
                base64_img2 = img2base64(img2)

                result_base64, difference = compare_explore(base64_img1, base64_img2)
                if difference:
                    mismatch_list.append(i + 1)
                    base64_strings.append(result_base64)
                # output_path = os.path.join(output_dir, f"{i + 1}.jpg")
                # base64_to_image(result_base64, output_path)
            else:
                result_base64 = draw_red_frame(base64_img1)  # 使用绘制红框的函数
                base64_strings.append(result_base64)
                # output_path = os.path.join(output_dir, f"{i + 1}.jpg")
                # base64_to_image(result_base64, output_path)
                mismatch_list.append(i + 1)

    mismatch_list, base64_strings, continuous = process_mismatch_lists(mismatch_list, base64_strings, threshold=10)
    # save_Diffpdf(username, doc1, doc2, file1_name, file2_name, CODE_SUCCESS,
    #             mismatch_list, base64_strings, continuous, None)
    doc1.close()
    doc2.close()
    return CODE_SUCCESS, mismatch_list, base64_strings, continuous, None


# if __name__ == "__main__":
#     main("username", '7.pdf', '8.pdf',"file1_name", "file2_name", 18, 17)
class FullPageHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file1, file2,file1_name, file2_name, page_num1, page_num2):
        return check_diff_pdf(username, file1, file2,file1_name, file2_name, page_num1, page_num2)
    async def post(self):
        username = self.current_user
        param = tornado.escape.json_decode(self.request.body)
        file_path_1 = param['file_path_1']
        file_path_2 = param['file_path_2']
        page_num1 = int(param['start_1'])
        page_num2 = int(param['start_2'])
        filename1 = os.path.basename(file_path_1)
        filename2 = os.path.basename(file_path_2)
        code, pages, imgs_base64, error_msg, msg = await self.process_async(username,
                                                                           file_path_1, file_path_2, filename1,
                                                                           filename2, page_num1, page_num2)
        custom_data = {
            "code": code,
            "data": {
                'pages': pages,
                'imgs_base64': imgs_base64,
                'error_msg': error_msg
            },
            "msg": msg
        }
        self.write(custom_data)