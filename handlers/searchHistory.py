import tornado
from tornado.concurrent import run_on_executor
from main import MainHandler, need_auth
import json
from model import db_result
import datetime

CODE_SUCCESS = 0
CODE_ERROR = 1


def searchHistory(timestamp, username, type_id, file_md5):
    if type_id and type_id in ['003', '004', '005', '007', '008', '009']:
        # Convert the timestamp to a datetime object
        dt_object = datetime.datetime.fromtimestamp(timestamp)
        # Format the datetime object to a string in 'YYYY-MM-DD' format
        formatted_date = dt_object.strftime('%Y-%m-%d')
        # 查询文本内容
        result = db_result.query_record(formatted_date, username, type_id, file_md5)
        return result


class SearchHistoryHandler(MainHandler):
    @run_on_executor
    def process_async(self, timestamp, username, type_id, file_md5):
        return searchHistory(timestamp, username, type_id, file_md5)

    @need_auth
    async def post(self):
        params = tornado.escape.json_decode(self.request.body)
        username = params['username']
        datetime = params['datetime']
        type_id = params['type_id']
        file_path = params['file_path']
        datetime = datetime / 1000
        result = await self.process_async(datetime, username, type_id, file_path)
        custom_data = {
            "code": CODE_SUCCESS,
            "data": result,
            "msg": ''
        }
        self.write(custom_data)
