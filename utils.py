from io import BytesIO
import base64
from collections import defaultdict
import cv2
import fitz
import numpy as np
from PIL import Image
from config import BASE64_PNG, FRONT
import os


def is_image(page):
    '''通过页面矢量元素的数量判断是否为图'''
    vector_count = len(page.get_cdrawings())
    print(vector_count)
    return vector_count > 1000


def page2img(page, dpi):
    '''pdf转png'''
    img = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
    img_pil = Image.frombytes("RGB", [img.width, img.height], img.samples)
    grayscale_img = img_pil.convert('1')
    buffered = BytesIO()
    grayscale_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"{BASE64_PNG}{img_base64}"


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


def base64_to_image(base64_str):
    """
    将Base64字符串转换为PIL图像对象
    """
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))
    return image


def image_to_base64(image):
    """
    将PIL图像对象转换为Base64字符串
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def process_paths(paths):
    processed_paths = []
    for p in paths:
        if p.startswith('.'):
            p = p[1:]  # Remove the leading '.'
        processed_paths.append(FRONT + p)
    return processed_paths
def add_url(path):
    if path.startswith('.'):
        path = path[1:]  # Remove the leading '.'
    url = f"{FRONT}{path}"
    return url


def merge_records(records):
    """
       合并查区域对比和实物对比，两个文件多图片
    """
    merged_records = defaultdict(lambda: {
        "username": "",
        "datetime": "",
        "type_id": "",
        "text": "",
        "images": [],
        "related_files": [],
        "result_file": ""
    })

    for record in records:
        key = tuple((f['file_name'], f['file_path']) for f in record['related_files'])
        if not merged_records[key]['username']:
            merged_records[key]['username'] = record['username']
            merged_records[key]['type_id'] = record['type_id']
            merged_records[key]['text'] = record['text']
            merged_records[key]['related_files'] = record['related_files']
        merged_records[key]['images'].extend(record['images'])
        merged_records[key]['datetime'] = max(merged_records[key]['datetime'], record['datetime'])

    return list(merged_records.values())


def convert_files_to_bytesio(excel_file_path):
    """
           将excel转换为字节流
    """

    # 读取Excel文件内容到字节流
    with open(excel_file_path, 'rb') as f:
        excel_file_bytes = f.read()
    excel_file_stream = BytesIO(excel_file_bytes).getvalue()
    return excel_file_stream

def ensure_directory_exists(file_path):
    # 确保目录存在
    # 获取文件的目录路径
    directory = os.path.dirname(file_path)
    # 检查这个目录是否存在
    if not os.path.exists(directory):
        # 如果目录不存在，则创建它
        os.makedirs(directory)
        print(f"目录 {directory} 已创建。")
    else:
        print(f"目录 {directory} 已存在。")
