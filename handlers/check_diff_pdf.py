import cv2
import numpy as np
from skimage.metrics import structural_similarity
import base64
from io import BytesIO
from skimage.metrics import structural_similarity as ssim
from PIL import Image, ImageChops, ImageStat
import os
import fitz
from config import BASE64_PNG
from utils import base64_to_image, img2base64, image_to_base64

CODE_SUCCESS = 0
CODE_ERROR = 1

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor




def pad_image(image, target_size, color=(255, 255, 255, 0)):
    original_size = image.size
    new_image = Image.new("RGBA", target_size, color)
    new_image.paste(image, (0, 0))
    return new_image

def crop_image(image, crop_size):
    return image.crop((0, 0, crop_size[0], crop_size[1]))

def compare_images(image1_base64, image2_base64):
    differece = True
    image_one = base64_to_image(image1_base64).convert('RGB')
    image_two = base64_to_image(image2_base64).convert('RGB')

    if image_one.size != image_two.size:
        width_one, height_one = image_one.size
        width_two, height_two = image_two.size

        if width_two < width_one or height_two < height_one:
            image_two = pad_image(image_two, (width_one, height_one))
        elif width_two > width_one or height_two > height_one:
            image_two = crop_image(image_two, (width_one, height_one))

    image_one_cv = cv2.cvtColor(np.array(image_one), cv2.COLOR_RGB2BGR)
    image_two_cv = cv2.cvtColor(np.array(image_two), cv2.COLOR_RGB2BGR)

    gray_image_one = cv2.cvtColor(image_one_cv, cv2.COLOR_BGR2GRAY)
    gray_image_two = cv2.cvtColor(image_two_cv, cv2.COLOR_BGR2GRAY)

    score, diff = ssim(gray_image_one, gray_image_two, full=True)
    print("SSIM: {}".format(score))

    diff = (diff * 255).astype("uint8")
    absdiff = cv2.absdiff(image_one_cv, image_two_cv)
    absdiff_gray = cv2.cvtColor(absdiff, cv2.COLOR_BGR2GRAY)
    _, absdiff_thresh = cv2.threshold(absdiff_gray, 30, 255, cv2.THRESH_BINARY)
    print(np.count_nonzero(absdiff_thresh))
    if np.count_nonzero(absdiff_thresh) < 20:
        differece = False
        image_base64 = image_to_base64(image_one)
        return f"{BASE64_PNG}{image_base64}", differece

    red_image = np.zeros_like(image_one_cv)
    red_image[:, :] = [0, 0, 255]

    highlighted_image = np.where(absdiff_thresh[..., None], red_image, image_one_cv)
    highlighted_image = Image.fromarray(cv2.cvtColor(highlighted_image, cv2.COLOR_BGR2RGB))

    image_base64 = image_to_base64(highlighted_image)
    return f"{BASE64_PNG}{image_base64}", differece


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

                result_base64, difference = compare_images(base64_img1, base64_img2)
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

                result_base64, difference = compare_images(base64_img1, base64_img2)
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