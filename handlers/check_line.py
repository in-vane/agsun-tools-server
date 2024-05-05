import fitz  # PyMuPDF
import time
import base64
import io
from io import BytesIO  # 从 io 模块导入 BytesIO 类

from save_filesys_db import save_Line

CODE_SUCCESS = 0
CODE_ERROR = 1

def thicken_lines_in_all_pages(doc, new_line_width=0.5):
    for page_number in range(len(doc)):
        if page_number == 6:
            page = doc[page_number]
            # Initialize a new shape object on the page to draw the modified lines
            shape = page.new_shape()
            # Analyze the page for vector drawings
            for item in page.get_drawings():
                if item['type'] == 's' and item['width'] < 0.08 and item['stroke_opacity'] == 1.0 and item[
                    'dashes'] == "[] 0":
                    for subitem in item['items']:
                        if subitem[0] == 'l':  # Check for line items
                            start_point, end_point = subitem[1], subitem[2]
                            new_color = (1, 0, 0)  # Red color
                            shape.draw_line(start_point, end_point)
                            shape.finish(width=new_line_width, color=new_color, stroke_opacity=item['stroke_opacity'])
            # Commit the drawing operations to the page
            shape.commit()

    # doc.save(PDF_OUTPUT)


def pdf_to_base64(doc):
    # 创建一个字节流
    pdf_stream = io.BytesIO()

    # 将文档保存到字节流
    doc.save(pdf_stream)

    # 获取字节流的内容
    pdf_bytes = pdf_stream.getvalue()

    # 将字节流编码为 Base64 字符串
    base64_str = base64.b64encode(pdf_bytes).decode('utf-8')

    # 关闭字节流
    pdf_stream.close()

    return base64_str

def check_line(username, file, filename):
    doc = fitz.open(stream=BytesIO(file))
    # doc = fitz.open(pdf_path)
    start = time.time()
    thicken_lines_in_all_pages(doc)
    base64_pdf = pdf_to_base64(doc)
    end = time.time()
    print(f'{end - start}秒')
    # save_Line(username, doc, filename, CODE_SUCCESS,'')
    doc.close()
    return CODE_SUCCESS, base64_pdf, ''


# pdf_path = '1.pdf'  # Replace with the path to your PDF file
# _,base64_pdf,_ = check(pdf_path)

