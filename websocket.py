import os
import base64

import cv2
import numpy as np


def img2base64(img):
    _, image_buffer = cv2.imencode('.jpg', img)
    image_base64 = base64.b64encode(image_buffer).decode('utf-8')
    return image_base64


def base642cv2img(base64_data):
    image_data = base64.b64decode(base64_data)
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return image


class FileAssembler:
    def __init__(self, file_name, total_slices):
        self.file_name = file_name
        self.total_slices = total_slices
        self.received_slices = {}
        self.received_data = b''  # 用于存储所有分片数据
    
    def add_slice(self, current_slice, file_data):
        self.received_slices[current_slice] = file_data
    
    def is_complete(self):
        return len(self.received_slices) == self.total_slices
    
    def assemble(self):
        if not self.is_complete():
            return None
        
        # Sort received slices by current slice number
        sorted_slices = sorted(self.received_slices.items(), key=lambda x: x[0])
        
        for _, slice_data in sorted_slices:
            b64 = slice_data.split(",", 1)
            self.received_data += base64.b64decode(b64[1])
        
        # output_path = self.file_name
        output_path = './python/assets/pdf/'
        # 如果目录不存在，则创建它
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 指定文件路径
        output_path = os.path.join(output_path, self.file_name)
        with open(output_path, "wb") as output_file:
            output_file.write(self.received_data)
        
        return output_path