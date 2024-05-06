import os
import asyncio
import tornado
import tornado.web
import tornado.websocket
import tornado.options
import tornado.ioloop


import handlers
from config import CONTENT_TYPE_PDF
from websocket import FileAssembler, pdf2img_split, write_file_name
from auth import decode_jwt
from concurrent.futures import ThreadPoolExecutor


def need_auth(method):
    def wrapper(self, *args, **kwargs):
        is_auth = getattr(self, 'is_auth', True)
        if not is_auth:
            return
        return method(self, *args, **kwargs)
    return wrapper


class Application(tornado.web.Application):
    def __init__(self):
        router = [
            (r'/api', MainHandler),
            (r'/api/login', handlers.LoginHandler),
            # (r'/api/logout', LogoutHandler),
            (r'/api/area', handlers.AreaHandler),
            (r'/api/fullPage', handlers.FullPageHandler),
            (r'/api/partCount', handlers.PartCountHandler),
            (r'/api/pageNumber', handlers.PageNumberHandler),
            (r'/api/line', handlers.LineHandler),
            # (r'/api/table', TableHandler),
            (r'/api/screw/bags', handlers.ScrewHandler),
            (r'/api/screw/compare', handlers.ScrewHandler),
            (r'/api/language', handlers.LanguageHandler),
            (r'/api/ce', handlers.CEHandler),
            (r'/api/size', handlers.SizeHandler),
            (r'/api/ocr_char', OcrHandler),
            (r'/api/ocr_icon', OcrHandler),
            (r"/websocket", WebSocketHandler),
        ]
        settings = {
            'debug': True
        }
        super().__init__(router, **settings)


class MainHandler(tornado.web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=10)

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', '*')
        self.set_header('Access-Control-Allow-Headers',
                        'Content-Type, Authorization')
        self.set_header('Access-Control-Expose-Headers',
                        'Content-Type, Authorization')

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
            # user_info = decode_jwt(token)
            userinfo = {'username': 'admin'}
            if userinfo:
                self.current_user = userinfo
            else:
                # Token无效，抛出一个403 Forbidden异常
                self.is_auth = False
                self.set_status(403)
                self.write({"error": "Invalid token"})
        else:
            # 如果没有提供Token，抛出一个401 Unauthorized异常
            self.is_auth = False
            self.set_status(401)
            self.write({"error": "Token not provided"})


# class LoginHandler(MainHandler):
#     async def post(self):
#         params = tornado.escape.json_decode(self.request.body)
#         username = params['username']
#         password = params['password']
#         code, token, message = await handlers.login(username, password)
#         custom_data = {
#             'code': code,
#             'data': {
#                 'access_token': token,
#                 'userinfo': {
#                     'name': username
#                 }
#             },
#             'message': message
#
#         }
#         self.write(custom_data)
#
#
# class LogoutHandler(MainHandler):
#     async def post(self):
#         code, username, msg = await handlers.logout()
#         custom_data = {
#             'code': code,
#             'data': {
#                 'username': username
#             },
#             'msg': msg
#
#         }
#         self.write(custom_data)


class FullPageHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user
        param = tornado.escape.json_decode(self.request.body)
        file_path_1 = param['file_path_1']
        file_path_2 = param['file_path_2']
        page_num1 = int(param['start_1'])
        page_num2 = int(param['start_2'])
        filename1 = os.path.basename(file_path_1)
        filename2 = os.path.basename(file_path_2)
        code, pages, imgs_base64, error_msg, msg = handlers.check_diff_pdf(username,
                                                                           file_path_1, file_path_2, filename1, filename2, page_num1, page_num2)
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


# class PartCountHandler(MainHandler):
#     @need_auth
#     def post(self):
#         username = self.current_user
#         params = tornado.escape.json_decode(self.request.body)
#         filename = params['filename']
#         rect = params['rect']
#         print(rect)
#         # 使用列表切片获取除第一项之外的所有元素，并使用列表推导式将它们转换为整数
#         # rect_int= [int(x) for x in rect[1:]]
#         rect_int = [int(x) for x in rect]
#         xmin = rect_int[0]
#         ymin = rect_int[1]
#         xmax = (rect_int[0] + rect_int[2])
#         ymax = (rect_int[1] + rect_int[3])
#         scale_factor = 72/300
#         pdf_rect = [xmin * scale_factor, ymin * scale_factor,
#                     xmax * scale_factor, ymax * scale_factor]
#         print(pdf_rect)
#         page_number_explore = int(params['page_explore'])
#         page_number_table = int(params['page_table'])
#         page_columns = int(params['columnCount'])
#         page_pair_index = params['pair_index']
#         print(page_columns, page_pair_index)
#         custom_data = handlers.check_part_count(
#             username, filename, pdf_rect, page_number_explore, page_number_table, page_columns, page_pair_index)
#
#         self.write(custom_data)


class PageNumberHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user

        params = tornado.escape.json_decode(self.request.body)
        print(params)
        file = params['file_path']
        rect = params['rect']
        rect = [value * 72 / 300 for value in rect]
        filename = os.path.basename(file)
        code, error, error_page, result, msg = handlers.check_page_number(username,
                                                                          file, filename, rect)
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


# class TableHandler(MainHandler):
#     @need_auth
#     def post(self):
#         username = self.current_user
#         page_number = int(self.get_argument('pageNumber'))
#         files = self.get_files()
#         file = files[0]
#         body = file["body"]
#         base64_imgs, error_pages = handlers.compare_table(body, page_number)
#         custom_data = {
#             "base64_imgs": base64_imgs,
#             "error_pages": error_pages,
#         }
#         self.write(custom_data)


class ScrewHandler(MainHandler):
    @need_auth
    def post(self):
        if self.request.path == "/api/screw/bags":
            param = tornado.escape.json_decode(self.request.body)
            rect = param['rect']
            page = param['page']
            file = param['file_path']
            # 修改宽度 (w) 和高度 (h)
            rect = [value * 72 / 300 for value in rect]
            code, data, msg = handlers.get_Screw_bags(file, page, rect)
        elif self.request.path == "/api/screw/compare":
            username = self.current_user
            params = tornado.escape.json_decode(self.request.body)
            print(params)
            file = params['file_path']
            table = params['table']
            start = int(params['start'])
            end = int(params['end'])
            file_name = os.path.basename(file)
            print("文件名:", file_name)
            code, data, msg = handlers.check_screw(
                username, file, file_name, table, start, end)
        else:
            code = 1
            data = {}
            msg = '请检查你的网址'
        custom_data = {
            'code': code,
            'data': data,
            'msg': msg
        }
        self.write(custom_data)


class LanguageHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user
        limit = int(self.get_argument('limit'))
        files = self.get_files()
        file = files[0]
        body = file["body"]
        filename = file["filename"]
        code, data, msg = handlers.check_language(
            username, body, filename, limit)

        custom_data = {
            'code': code,
            'data': data,
            'msg': msg
        }

        self.write(custom_data)


class LineHandler(MainHandler):
    @need_auth
    def post(self):
        param = tornado.escape.json_decode(self.request.body)
        username = self.current_user
        file = param['file_path']
        file_name = os.path.basename(file)
        code, path, msg = handlers.check_line(
            username, file, file_name)
        custom_data = {
            'code': code,
            'data': {
                'path':path
            },
            'msg': msg
        }
        self.write(custom_data)


class CEHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user
        mode = self.get_argument('mode', default='0')
        mode = int(mode)  # 确保将模式转换为整数
        num = int(self.get_argument('sheet'))
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
            code, image_base64, msg = handlers.check_CE_mode_normal(username,
                                                                    file_excel, file_pdf, pdf_name, excel_name, num)
        custom_data = {
            "code": code,
            "data": {
                "image_base64": image_base64
            },
            "msg": msg
        }
        self.write(custom_data)


class OcrHandler(MainHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.MODE_CHAR = 0
        self.MODE_ICON = 1

    @need_auth
    def post(self):
        username = self.current_user
        filename = self.get_argument('filename')
        mode = int(self.get_argument('mode'))
        page_num = int(self.get_argument('page'))
        crop = self.get_argument('crop')
        custom_data = {}
        if mode == self.MODE_CHAR:
            print("== MODE_CHAR ==")
            custom_data = handlers.check_ocr_char(filename, crop, page_num)
        if mode == self.MODE_ICON:
            print("== MODE_ICON ==")
            custom_data = handlers.check_ocr_icon(filename, crop, page_num)

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
            if type == 'upload':
                await write_file_name(self, file_path, options)
            if type == 'pdf2img':
                await pdf2img_split(self, file_path, options)
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


def main():
    tornado.options.define("port", default=8888,
                           help="run on the given port", type=int)
    print('ready')
    tornado.options.parse_command_line()
    app = Application()
    app.listen(tornado.options.options.port)
    # await asyncio.Event().wait()
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    # asyncio.run(main())  # 这是 Python 3.7 引入的新特性
    main()
