import os
import base64
import fitz
from config import PATH_PDF, BASE64_PNG
from utils import is_image, page2img


MODE_NORMAL = 0
MODE_VECTOR = 1


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
        sorted_slices = sorted(
            self.received_slices.items(), key=lambda x: x[0])

        for _, slice_data in sorted_slices:
            b64 = slice_data.split(",", 1)
            self.received_data += base64.b64decode(b64[1])

        output_path = PATH_PDF
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        output_path = os.path.join(output_path, self.file_name)
        with open(output_path, "wb") as output_file:
            output_file.write(self.received_data)

        return output_path


async def pdf2img_split(ws, pdf_path, options):
    '''pdf按页转png'''
    print("===== begin pdf2img =====")
    doc = fitz.open(pdf_path)
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
        img_base64 = ""

        if (options['mode'] == MODE_NORMAL):
            img_base64 = page2img(page, dpi=300)
        if (options['mode'] == MODE_VECTOR):
            if is_image(page):
                img_base64 = page2img(page, dpi=300)

        img_base64 = "" if not img_base64 else f"{BASE64_PNG}{img_base64}"
        await ws.write_message({
            "total": end - start,
            "current": page_number - start + 1,
            "img_base64": img_base64,
            "options": options
        })

    doc.close()
    print("===== done =====")


async def write_file_name(ws, file_path, options):
    '''往前端返回上传文件所在的路径'''
    await ws.write_message({
        "file_path": file_path,
        "options": options
    })
