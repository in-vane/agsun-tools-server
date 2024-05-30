import io
import os
import base64
import hashlib

import fitz
import pymysql
from config import PATH_PDF, FLIES_ROOT
from utils import page2img
from model import db_files


MODE_NORMAL = 0
MODE_VECTOR = 1


class FileAssembler:
    def __init__(self, username, file_name, total_slices):
        self.username = username
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
        sorted_slices = sorted(
            self.received_slices.items(), key=lambda x: x[0])

        for _, slice_data in sorted_slices:
            b64 = slice_data.split(",", 1)
            self.received_data += base64.b64decode(b64[1])

        output_path = FLIES_ROOT  # 替换为实际输出路径

        if not os.path.exists(output_path):
            os.makedirs(output_path)
        md5_hash = hashlib.md5(self.received_data).hexdigest()
        file_name = f"{md5_hash}.pdf"
        output_path = os.path.join(output_path, file_name)
        with open(output_path, "wb") as output_file:
            output_file.write(self.received_data)
        print(self.username)
        print(output_path)
        try:
            db_files.insert_file_record(self.username, self.file_name, md5_hash, output_path)
        except pymysql.MySQLError as err:
            if err.args[0] == 1062:  # Duplicate entry error code
                print(
                    f"Duplicate entry for {self.file_name} with hash {md5_hash}")
            else:
                print(f"Error occurred while inserting file record: {err}")

        return output_path


async def pdf2img(ws, file_path, options):
    print("===== begin =====")
    doc = fitz.open(file_path)
    total = len(doc)
    start = 0
    end = total
    if 'start' in options:
        start = max(0, int(options['start']) - 1)
    if 'end' in options:
        end = min(total, int(options['end']))
    print(f"from {start} to {end}")

    for page_number in range(start, end):
        page = doc.load_page(page_number)
        img_base64 = page2img(page, dpi=300)
        await ws.write_message({
            "total": end - start,
            "current": page_number - start + 1,
            "img_base64": img_base64,
        })
    await ws.write_message({
        "complete": 'pdf2img'
    })

    doc.close()
    print("===== done =====")
