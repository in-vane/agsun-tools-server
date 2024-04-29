from tornado import gen

from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor
from tornado.ioloop import IOLoop
import time

from main import MainHandler

import sys
sys.path.append("..")


def sleep():
    time.sleep(3)
    return 'Finish'


class TestHandler(MainHandler):
    executor = ThreadPoolExecutor(max_workers=10)

    @run_on_executor
    def sleep_async(self):
        return sleep()

    async def post(self):
        url = self.request.path
        print(f"start {url}")
        result = await self.sleep_async()
        self.write(f"{url}: {result}")
