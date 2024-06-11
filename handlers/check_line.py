import fitz  # PyMuPDF
import time
import base64
import io
import os
from io import BytesIO  # 从 io 模块导入 BytesIO 类

from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor

from save_filesys_db import save_Line
from utils import add_url

CODE_SUCCESS = 0
CODE_ERROR = 1


def thicken_lines_in_all_pages(doc, mode, start, end, new_line_width=0.85, detection_line_width=0.08, highlight_color=(1, 0, 0)):
    if mode == 0:
        print("报红模式")
    else:
        print("加粗模式")
    if start == -1 and end == -1:
        start = 0
        end = len(doc) - 1
    else:
        start = start -1
        end =end-1

    for page_number in range(start, end + 1):
        page = doc[page_number]
        print(f"正在检测{page_number+1}")
        # Initialize a new shape object on the page to draw the modified lines
        shape = page.new_shape()
        # Analyze the page for vector drawings
        for item in page.get_drawings():
            width_in_pt = item['width']
            width_in_mm = width_in_pt * (25.4 / 72)
            if item['type'] == 's' and width_in_mm < detection_line_width and item['stroke_opacity'] == 1.0 and item['dashes'] == "[] 0":
                for subitem in item['items']:
                    if subitem[0] == 'l':  # Check for line items
                        start_point, end_point = subitem[1], subitem[2]
                        if mode == 0:  # Highlight mode
                            shape.draw_line(start_point, end_point)
                            shape.finish(width=width_in_pt, color=highlight_color, stroke_opacity=item['stroke_opacity'])
                        elif mode == 1:  # Thicken mode
                            shape.draw_line(start_point, end_point)
                            shape.finish(width=new_line_width, color=item['color'], stroke_opacity=item['stroke_opacity'])
        # Commit the drawing operations to the page
        shape.commit()


    # doc.save(PDF_OUTPUT)


def check_line(username, file, file_name, mode, start, end):
    doc = fitz.open(file)
    thicken_lines_in_all_pages(doc, mode, start, end)
    output_path = save_Line(username['username'], doc, file, file_name, CODE_SUCCESS, '')
    url = add_url(output_path)
    print(f"url:{url}")
    return CODE_SUCCESS, url, ''


# pdf_path = '1.pdf'  # Replace with the path to your PDF file
# _,base64_pdf,_ = check(pdf_path)
class LineHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file, file_name, mode, start, end):
        return check_line(username, file, file_name, mode, start, end)

    async def post(self):
        param = tornado.escape.json_decode(self.request.body)
        username = self.current_user
        print(param)
        file = param['file_path']
        mode = param['mode']
        start = int(param.get('start', -1))
        end = int(param.get('end', -1))
        file_name = os.path.basename(file)
        code, path, msg = await self.process_async(
            username, file, file_name, mode, start, end)
        custom_data = {
            'code': code,
            'data': {
                'path': path
            },
            'msg': msg
        }
        self.write(custom_data)
