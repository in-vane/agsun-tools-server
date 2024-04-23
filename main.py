import asyncio
import tornado
import tornado.web
import tornado.websocket
import tornado.options
import tornado.ioloop
import os
import tasks
from config import CONTENT_TYPE_PDF
from websocket import FileAssembler, pdf2img_split, write_file_name
from auth import decode_jwt, MOCK_TOKEN


def need_auth(method):
    def wrapper(self, *args, **kwargs):
        is_auth = getattr(self, 'is_auth', True)
        if not is_auth:
            return
        return method(self, *args, **kwargs)
    return wrapper


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
            (r'/api/screw/bags', ScrewHandler),
            (r'/api/screw/compare', ScrewHandler),
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


class LoginHandler(MainHandler):
    def post(self):
        param = tornado.escape.json_decode(self.request.body)
        username = param['username']
        password = param['password']
        code, token, message = tasks.login(username, password)
        # code, token, message = 0, MOCK_TOKEN, 'ok'
        custom_data = {
            'code': code,
            'data': {
                'access_token': token
            },
            'message': message

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


class ExploreHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user
        img_1 = self.get_argument('img_1')
        img_2 = self.get_argument('img_2')
        img_base64 = tasks.compare_explore(img_1, img_2)
        custom_data = {
            "result": img_base64
        }
        self.write(custom_data)


class FullPageHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user
        param = tornado.escape.json_decode(self.request.body)
        file_path_1 = param['file_path_1']
        file_path_2 = param['file_path_2']
        page_num1 = int(param['start_1'])
        page_num2 = int(param['start_2'])
        code, pages, imgs_base64, error_msg, msg = tasks.check_diff_pdf(username,
                                                                        file_path_1, file_path_2, '1', '2', page_num1, page_num2)
        # files = self.get_files()
        # file1 = files[0]
        # body1 = file1["body"]
        # filename1 = file1.get("filename")
        # file2 = files[1]
        # body2 = file2["body"]
        # filename2 = file2.get("filename")
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
    @need_auth
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

        custom_data = tasks.check_part_count(
            username, filename, pdf_rect, page_number_explore, page_number_table)

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
    @need_auth
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
    @need_auth
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
    @need_auth
    def post(self):
        if self.request.path == "/api/screw/bags":
            param = tornado.escape.json_decode(self.request.body)
            img_base64 = param['crop']
            code, data, msg = tasks.get_Screw_bags(img_base64)
        elif self.request.path == "/api/screw/compare":
            username = self.current_user
            # files = self.get_files()
            # file = files[0]
            # body = file["body"]
            # filename = file["filename"]
            params = tornado.escape.json_decode(self.request.body)
            print(params)
            file = params['file_path']
            table = params['table']
            start = int(params['start'])
            end = int(params['end'])
            file_name = os.path.basename(file)
            print("文件名:", file_name)
            code, data, msg = tasks.check_screw(username, file, file_name, table, start, end)
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
        code, data, msg = tasks.check_language(username, body, filename, limit)

        custom_data = {
            'code': code,
            'data': data,
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
            code, image_base64, msg = tasks.check_CE_mode_normal(username,
                                                                 file_excel, file_pdf, pdf_name, excel_name, num)
        custom_data = {
            "code": code,
            "data": {
                "image_base64": image_base64
            },
            "msg": msg
        }
        self.write(custom_data)


class SizeHandler(MainHandler):
    @need_auth
    def post(self):
        username = self.current_user
        files = self.get_files()
        file = files[0]
        filename, content_type, body = file["filename"], file["content_type"], file["body"]
        width = int(self.get_argument('width', default='-1'))
        height = int(self.get_argument('height', default='-1'))
        
        error, msg, img_base64 = tasks.check_size(body, width, height)
        custom_data = {
            "code": 0,
            "data": {
                "error": error,
                "img_base64": img_base64
            },
            "msg": msg,
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
    print('ready')
    tornado.options.parse_command_line()
    app = Application()
    app.listen(tornado.options.options.port)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
