from main import MainHandler
import tornado
from tornado.concurrent import run_on_executor
import datetime
import sys

sys.path.append("..")
import json

CODE_SUCCESS = 0
CODE_ERROR = 1
from model import db_files


def select_file(timestamp, username, type_id):
    # Convert the timestamp to a datetime object
    dt_start = datetime.datetime.fromtimestamp(timestamp[0])
    dt_end = datetime.datetime.fromtimestamp(timestamp[1])
    # Format the datetime object to a string in 'YYYY-MM-DD' format
    timestamp[0] = dt_start.strftime('%Y-%m-%d')
    timestamp[1] = dt_end.strftime('%Y-%m-%d')
    # Determine the table name based on type_id
    table_map = {
        '001': 'area',
        '002': 'diff_pdf',
        '003': 'result',
        '004': 'result',
        '005': 'result',
        '006': 'ce',
        '007': 'result',
        '008': 'result',
        '009': 'ocr',
        '010': 'line_result_files'
    }
    table = table_map.get(type_id)
    result = db_files.query_files(table, timestamp, username, type_id)
    data = []
    seen_paths = set()

    for entry in result:
        if entry["file_path"] not in seen_paths:
            data.append(entry)
            seen_paths.add(entry["file_path"])
    return data


class Select_FileHandler(MainHandler):
    @run_on_executor
    def process_async(self, datetime, username, type_id):
        return select_file(datetime, username, type_id)

    async def post(self):
        params = tornado.escape.json_decode(self.request.body)
        print(params)
        datetime = params['datetime']
        username = params['username']
        type_id = params['type_id']
        datetime[0] = datetime[0] / 1000
        datetime[1] = datetime[1] / 1000
        data = await self.process_async(datetime, username, type_id)

        custom_data = {
            "code": 0,
            "data": data,
            "msg": ''
        }

        self.write(custom_data)
