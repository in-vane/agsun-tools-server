import tornado
from tornado.concurrent import run_on_executor
from main import MainHandler, need_auth
from model import db_files
import datetime


import sys
sys.path.append("..")


def check_md5(file_md5):
    try:
        file_info = db_files.query_file_by_md5(file_md5)
        if file_info and 'datetime' in file_info and isinstance(file_info['datetime'], datetime.datetime):
            file_info['datetime'] = file_info['datetime'].isoformat()
        print(f"file_info {file_info}")
        return file_info
    except Exception as e:
        print(f"Error querying file info: {e}")
        return None


class FileHandler(MainHandler):
    @run_on_executor
    def process_async(self, file_md5):
        return check_md5(file_md5)

    @need_auth
    async def post(self):
        username = self.current_user
        params = tornado.escape.json_decode(self.request.body)
        file_md5 = params['md5']
        print(file_md5)
        result = await self.process_async(file_md5)
        custom_data = {
            "code": 0,
            "data": {
                "result": result
            },
            "msg": ''
        }

        self.write(custom_data)
