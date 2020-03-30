# -*- coding: utf-8 -*-

import schedule
import time
from order_engine import *

def order_engine_job():
    print("Running order_engine...")
    o = OrderEngine()
    o.run()

schedule.every(1).minutes.do(order_engine_job)

while True:
    schedule.run_pending()
    time.sleep(10)
