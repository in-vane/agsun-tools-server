import asyncio
import tornado
import tornado.web
import tornado.websocket
import tornado.options
import tornado.ioloop
import tasks
from config import CONTENT_TYPE_PDF
from websocket import FileAssembler, pdf2img_split, write_file_name
from tornado.web import HTTPError
from auth import decode_jwt

# 创建一个新的基础处理器，包含JWT验证逻辑
class BaseHandler(tornado.web.RequestHandler):
    def prepare(self):
        # 登录和注销请求不需要Token验证
        if self.request.path in ["/api/login", "/api/logout"]:
            return

        # 其他API请求都需要Token验证
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_info = decode_jwt(token)
            if user_info:
                self.current_user = user_info
            else:
                # Token无效，抛出一个403 Forbidden异常
                raise HTTPError(403, "Invalid token")
        else:
            # 如果没有提供Token，抛出一个401 Unauthorized异常
            raise HTTPError(401, "Token not provided")
class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/api', MainHandler),
            (r'/api/login', LoginHandler),
            (r'/api/logout', LogoutHandler),
            (r'/api/explore', ExploreHandler),
            (r'/api/fullPage', FullPageHandler),
            (r'/api/partCount', PartCountHandler),
            (r'/api/pageNumber', PageNumberHandler),
            (r'/api/table', TableHandler),
            (r'/api/screw', ScrewHandler),
            (r'/api/language', LanguageHandler),
            (r'/api/ce', CEHandler),
            (r'/api/size', SizeHandler),
            (r'/api/ocr_char', OcrHandler),
            (r'/api/ocr_icon', OcrHandler),
            (r"/websocket", WebSocketHandler),
        ]
        settings = {
            'debug': True
        }
        super().__init__(handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods',
                        'POST, GET, PUT, DELETE, OPTIONS')
        self.set_header('Access-Control-Allow-Headers', 'Content-Type')
        self.set_header('Access-Control-Expose-Headers', 'Content-Type')

    def options(self):
        self.set_status(200)
        self.finish()

    def get_files(self):
        files = []
        for field_name, file in self.request.files.items():
            files.append(file[0])
        return files

    def save_results(self):
        pass

    def prepare(self):
        # 登录和注销请求不需要Token验证
        if self.request.path in ["/api/login", "/api/logout"]:
            return

        # 其他API请求都需要Token验证
        auth_header = self.request.headers.get('Authorization')
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_info = decode_jwt(token)
            if user_info:
                self.current_user = user_info
            else:
                # Token无效，抛出一个403 Forbidden异常
                raise HTTPError(403, "Invalid token")
        else:
            # 如果没有提供Token，抛出一个401 Unauthorized异常
            raise HTTPError(401, "Token not provided")


class ExploreHandler(MainHandler):
    def post(self):
        username = self.current_user
        img_1 = self.get_argument('img_1')
        img_2 = self.get_argument('img_2')
        img_base64 = tasks.compare_explore(img_1, img_2)
        custom_data = {
            "result": img_base64
        }
        self.write(custom_data)


class LoginHandler(MainHandler):
    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        code, token, msg = tasks.login(username, password)
        custom_data = {
            'code': code,
            'data': {
                'user_info': token
            },
            'msg': msg

        }
        self.write(custom_data)


class LogoutHandler(MainHandler):
    def post(self):
        code, username, msg = tasks.logout()
        custom_data = {
            'code': code,
            'data': {
                'username': username
            },
            'msg': msg

        }
        self.write(custom_data)


class FullPageHandler(MainHandler):
    def post(self):
        username = self.current_user
        files = self.get_files()
        file1 = files[0]
        body1 = file1["body"]
        filename1 = file1.get("filename")
        file2 = files[1]
        body2 = file2["body"]
        filename2 = file2.get("filename")
        page_num1 = int(self.get_argument('page_num1'))
        page_num2 = int(self.get_argument('page_num2'))
        code, pages, imgs_base64, error_msg, msg = tasks.check_diff_pdf(
            username, body1, body2, filename1, filename2, page_num1, page_num2)

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


class PartCountHandler(MainHandler):
    def post(self):
        username = self.current_user
        filename = self.get_argument('filename')
        rect = self.get_arguments('rect')
        # 使用列表切片获取除第一项之外的所有元素，并使用列表推导式将它们转换为整数
        # rect_int= [int(x) for x in rect[1:]]
        rect_int = [int(x) for x in rect]
        xmin = rect_int[0]
        ymin = rect_int[1]
        xmax = (rect_int[0] + rect_int[2])
        ymax = (rect_int[1] + rect_int[3])
        pdf_rect = [xmin, ymin, xmax, ymax]
        print(pdf_rect)
        page_number_explore = int(self.get_argument('pageNumberExplore'))
        page_number_table = int(self.get_argument('pageNumberTable'))
        '''
        custom_data {
            code <int>: 状态码，用于表示处理结果的不同情况。
                0: 表示未检测到错误或者未找到满足条件的表格。
                1: 表示零件计数和明细表检测均成功。
                2: 表示零件计数成功，但明细表检测未发现错误。
                3: 表示零件计数给定页面表格出错，明细表检测成功。
            mapping_results <list>: 与零件计数相关的详细匹配结果.
                key     <string>: 被检测的数字文本。
                matched <bool>: 指示是否成功匹配。 True 表示匹配成功， False 表示失败。 
                found   <int>: 实际发现的匹配数量。
                expected<int | None>: 预期匹配的数量，如果第三列没有找到数字，则为 None 。
            error_pages <list>: 错误页的图片信息和相应的页面编号。
                images_base64 <list>: 错误页面的图片, 以Base64编码的字符串形式表示。
                page_numbers <list>: 对应的PDF页面编号。
            messages <string>: 一个字符串消息，提供关于处理结果的额外信息或错误消息。
        }
        '''
        custom_data = tasks.check_part_count(
            filename, pdf_rect, page_number_explore, page_number_table)

        # custom_data = {
        #     "error": error,
        #     "result": result,
        #     "table": {
        #         "error_pages": images_base64,
        #         "error_pages_no": error_pages,
        #     }
        # }

        self.write(custom_data)


class PageNumberHandler(MainHandler):
    def post(self):
        username = self.current_user
        files = self.get_files()
        file = files[0]
        body = file["body"]
        filename = file.get("filename")
        code, error, error_page, result, msg = tasks.check_page_number(username,
            body, filename)
        custom_data = {
            'code': code,
            'data': {
                "error": error,
                "error_page": error_page,
                "result": result
            },
            'msg': msg

        }
        self.write(custom_data)


class TableHandler(MainHandler):
    def post(self):
        username = self.current_user
        page_number = int(self.get_argument('pageNumber'))
        files = self.get_files()
        file = files[0]
        body = file["body"]
        base64_imgs, error_pages = tasks.compare_table(body, page_number)
        custom_data = {
            "base64_imgs": base64_imgs,
            "error_pages": error_pages,
        }
        self.write(custom_data)


class ScrewHandler(MainHandler):
    def post(self):
        username = self.current_user
        files = self.get_files()
        file = files[0]
        body = file["body"]
        filename = file["filename"]
        code, data, msg = tasks.check_screw(username, body, filename)
        custom_data = {
            'code': code,
            'data': data,
            'msg': msg
        }
        self.write(custom_data)


class LanguageHandler(MainHandler):
    def post(self):
        username = self.current_user
        limit = int(self.get_argument('limit'))
        files = self.get_files()
        file = files[0]
        body = file["body"]
        filename = file["filename"]
        code, data, msg = tasks.check_language(username, body, filename, limit)

        custom_data = {
            'code': code,
            'data': data,
            'msg': msg
        }

        self.write(custom_data)


class CEHandler(MainHandler):
    def post(self):
        username = self.current_user
        mode = self.get_argument('mode', default='0')
        mode = int(mode)  # 确保将模式转换为整数
        work_table = self.get_argument('work_table', default=None)
        files = self.get_files()
        file_1, file_2 = files[0], files[1]
        name1 = file_1["filename"]
        name2 = file_2["filename"]
        file_1_type, file_1_body = file_1["content_type"], file_1["body"]
        file_2_body = file_2["body"]
        if file_1_type == CONTENT_TYPE_PDF:
            file_pdf, file_excel = file_1_body, file_2_body
            pdf_name, excel_name = name1, name2
        else:
            file_pdf, file_excel = file_2_body, file_1_body
            pdf_name, excel_name = name2, name1
        img_base64 = ''
        if mode == 0:
            code, image_base64, msg = tasks.check_CE_mode_normal(username,
                file_excel, file_pdf, pdf_name, excel_name, work_table)
        custom_data = {
            "code": code,
            "data": {
                "image_base64": image_base64
            },
            "msg": msg
        }
        self.write(custom_data)


class SizeHandler(MainHandler):
    def post(self):
        username = self.current_user
        files = self.get_files()
        file = files[0]
        filename, content_type, body = file["filename"], file["content_type"], file["body"]
        error, error_msg, img_base64 = tasks.compare_size(body)
        custom_data = {
            "error": error,
            "error_msg": error_msg,
            "result": img_base64,
        }
        self.write(custom_data)


class OcrHandler(MainHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.MODE_CHAR = 0
        self.MODE_ICON = 1

    def post(self):
        username = self.current_user
        filename = self.get_argument('filename')
        mode = int(self.get_argument('mode'))
        page_num = int(self.get_argument('page'))
        crop = self.get_argument('crop')
        custom_data = {}
        if mode == self.MODE_CHAR:
            print("== MODE_CHAR ==")
            custom_data = tasks.check_ocr_char(filename, crop, page_num)
        if mode == self.MODE_ICON:
            print("== MODE_ICON ==")
            custom_data = tasks.check_ocr_icon(filename, crop, page_num)

        self.write(custom_data)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = {}

    def check_origin(self, origin):
        return True

    def open(self):
        print("websocket opened")

        self.temp_count = 0
        self.loop = tornado.ioloop.PeriodicCallback(
            self.check_per_seconds, 1000)
        self.loop.start()  # 启动一个循环，每秒向electron端发送数字，该数字在不断递增

    async def on_message(self, message):
        print("===== get_message =====")
        data = tornado.escape.json_decode(message)
        type = data.get('type')
        file_name = data.get('fileName')
        file_data = data.get('file')
        total = int(data.get('total'))
        current = int(data.get('current'))
        options = data.get('options')

        if file_name not in self.files:
            self.files[file_name] = FileAssembler(file_name, total)
        _file = self.files[file_name]
        _file.add_slice(current, file_data)

        if _file.is_complete():
            file_path = _file.assemble()
            if type == 'pdf2img':
                await pdf2img_split(self, file_path, options)
            if type == 'compare':
                await write_file_name(self, file_path, options)
            del self.files[file_name]

        custom_data = {"data": f"{file_name} {current}/{total}"}
        self.write_message(custom_data)

    def on_close(self):
        print("websocket closed")
        self.loop.stop()

    def check_per_seconds(self):
        self.write_message(tornado.escape.json_encode(
            {"data": self.temp_count}))
        self.temp_count += 1


async def main():
    tornado.options.define("port", default=8888,
                           help="run on the given port", type=int)
    tornado.options.parse_command_line()
    app = Application()
    app.listen(tornado.options.options.port)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
