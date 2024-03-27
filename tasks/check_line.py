import fitz  # PyMuPDF
import time
from io import BytesIO
import os
import base64

# 新版pdf转化为图片文件夹
PDF_OUTPUT = './python/assets/pdf/output.pdf'


def thicken_lines_in_all_pages(doc, new_line_width=0.5):
    for page_number in range(len(doc)):
        page = doc[page_number]
        print(page_number)
        # Initialize a new shape object on the page to draw the modified lines
        shape = page.new_shape()
        # Analyze the page for vector drawings
        for item in page.get_drawings():
            if item['type'] == 's' and item['width'] < 0.08 and item['stroke_opacity'] == 1.0 and item[
                'dashes'] == "[] 0":
                for subitem in item['items']:
                    if subitem[0] == 'l':  # Check for line items
                        start_point, end_point = subitem[1], subitem[2]

                        # Check if the line is horizontal by comparing the y-coordinates of the start and end points
                        if start_point.y == end_point.y:
                            # Redraw the line with the specified new line width and color (red in this example)
                           new_color = (1, 0, 0)  # Red color
                           shape.draw_line(start_point, end_point)
                           shape.finish(width=new_line_width, color=new_color, stroke_opacity=item['stroke_opacity'])
        # Commit the drawing operations to the page
        shape.commit()
    doc.save(PDF_OUTPUT)
    doc.close()


def pdf_to_base64():
    """将PDF文件转换为Base64编码的字符串"""
    # 首先，将PDF文件读取为字节流
    with open(PDF_OUTPUT, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()

    # 然后，将字节流编码为Base64字符串
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

    return base64_pdf

def check(pdf_path):
    doc = fitz.open(stream=BytesIO(pdf_path))
    # doc = fitz.open(pdf_path)
    start = time.time()
    thicken_lines_in_all_pages(doc)
    base64_pdf = pdf_to_base64()
    end = time.time()
    print(f'{end - start}秒')
    return base64_pdf
# 测试
# pdf_path = '1.pdf'  # Replace with the path to your PDF file
# check(pdf_path)

