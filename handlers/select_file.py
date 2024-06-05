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
    dt_object = datetime.datetime.fromtimestamp(timestamp)
    # Format the datetime object to a string in 'YYYY-MM-DD' format
    formatted_date = dt_object.strftime('%Y-%m-%d')
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
    result = db_files.query_files(table, formatted_date, username, type_id)
    return result


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
        datetime = datetime / 1000
        result = await self.process_async(datetime, username, type_id)

        custom_data = {
            "code": 0,
            "data": result,
            "msg": ''
        }

        self.write(custom_data)
