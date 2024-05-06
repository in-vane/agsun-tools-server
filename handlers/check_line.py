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

CODE_SUCCESS = 0
CODE_ERROR = 1
# PDF_OUTPUT = './assets/pdf/temp.pdf'

def thicken_lines_in_all_pages(doc, new_line_width=0.5):
    for page_number in range(len(doc)):
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


def check_line(username, file, filename):
    doc = fitz.open(file)
    thicken_lines_in_all_pages(doc)
    output_path = save_Line(username, doc, filename, CODE_SUCCESS,'')
    return CODE_SUCCESS, output_path, ''


# pdf_path = '1.pdf'  # Replace with the path to your PDF file
# _,base64_pdf,_ = check(pdf_path)
class LineHandler(MainHandler):
    @run_on_executor
    def process_async(self, username, file, filename):
        return check_line(username, file, filename)
    async def post(self):
        param = tornado.escape.json_decode(self.request.body)
        username = self.current_user
        file = param['file_path']
        file_name = os.path.basename(file)
        code, path, msg = await self.process_async(
            username, file, file_name)
        custom_data = {
            'code': code,
            'data': {
                'path': path
            },
            'msg': msg
        }
        self.write(custom_data)
