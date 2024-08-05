import tornado
from tornado.concurrent import run_on_executor
from main import MainHandler, need_auth
import json
from model import db_result, db_ce, db_diff_pdf, db_area, db_line_result_files, db_ocr
import datetime

CODE_SUCCESS = 0
CODE_ERROR = 1


def searchHistory(timestamp, username, type_id, file_path):
    # Convert the timestamp to a datetime object
    dt_start = datetime.datetime.fromtimestamp(timestamp[0])
    dt_end = datetime.datetime.fromtimestamp(timestamp[1])
    # Format the datetime object to a string in 'YYYY-MM-DD' format
    timestamp[0] = dt_start.strftime('%Y-%m-%d')
    timestamp[1] = dt_end.strftime('%Y-%m-%d')
    if type_id and type_id in ['003', '004', '005', '007', '008']:
        # 查询文本内容
        result = db_result.query_record(timestamp, username, type_id, file_path)
    elif type_id and type_id =='006':
        result = db_ce.query_record(timestamp, username, type_id, file_path)
    elif type_id and type_id =='001':
        result = db_area.query_record(timestamp, username, type_id, file_path)
    elif type_id and type_id == '002':
        result = db_diff_pdf.query_record(timestamp, username, type_id, file_path)
    elif type_id and type_id == '010':
        result = db_line_result_files.query_record(timestamp, username, type_id, file_path)
    elif type_id and type_id == '009':
        result = []
    else:
        result = []

    return result


class SearchHistoryHandler(MainHandler):
    @run_on_executor
    def process_async(self, timestamp, username, type_id, file_path):
        return searchHistory(timestamp, username, type_id, file_path)

    @need_auth
    async def post(self):
        params = tornado.escape.json_decode(self.request.body)
        username = params['username']
        datetime = params['datetime']
        type_id = params['type_id']
        file_path = params['file_path']
        datetime[0] = datetime[0] / 1000
        datetime[1] = datetime[1] / 1000
        result = await self.process_async(datetime, username, type_id, file_path)
        custom_data = {
            "code": CODE_SUCCESS,
            "data": result,
            "msg": ''
        }
        self.write(custom_data)
