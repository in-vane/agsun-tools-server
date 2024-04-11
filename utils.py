from io import BytesIO
import base64
import cv2
import fitz
import numpy as np
from PIL import Image


def is_image(page):
    '''通过页面矢量元素的数量判断是否为图'''
    vector_count = len(page.get_cdrawings())
    return vector_count > 1000


def page2img(page, dpi):
    '''pdf转png'''
    img = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
    img_pil = Image.frombytes("RGB", [img.width, img.height], img.samples)
    grayscale_img = img_pil.convert('1')
    buffered = BytesIO()
    grayscale_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_base64


def base642img(base64_data: str):
    '''解码base64为图像数据'''
    image_data = base64.b64decode(base64_data)
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return image


def img2base64(img):
    '''jpg转base64'''
    _, image_buffer = cv2.imencode(f'.jpg', img)
    image_base64 = base64.b64encode(image_buffer).decode('utf-8')
    return image_base64
