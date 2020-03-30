# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import crypto

class MACD:
    """computes MACD"""

    def __init__(self, market_symbol):
        self.market_symbol = market_symbol
        self.timeframe = '1d'
        self.limit = None
        self.crypto_client = crypto.Crypto(None, 'bittrex') # defaults to using Bittrex client for looking up exchange rates to USDT
        self.init_logger()

    def log(self, msg):
        msg = str(msg)
        print(msg)
        self.log_buffer.append(msg)
        self.logger.info(msg)

    def init_logger(self): 
        self.log_buffer = []
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        # create a file handler
        handler = logging.FileHandler('./crypto.log')
        handler.setLevel(logging.INFO)
        # create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        # add the handlers to the logger
        self.logger.addHandler(handler)
    
    def computeMACD(self):
        ema26 = self.getEMA(26)
        ema12 = self.getEMA(12)
        macd = [(ema26[i] - ema12[i]) for i in range(0, len(ema26))]
        ema9 = self.getEMA(9)
        self.log("MACD: %s" % (macd))
        self.log("9d EMA: %s" % (ema9))

    def calculator(self, days, data):
        alpha = 2 / (days + 1)
        previous = 0
        initialAccumulator = 0
        skip = 0
        results = []
        for i in range(0, len(data)):
			v = data[i][2]
			# if not previous and not v:
			# 	skip += 1
			if i < (days + skip - 1):
				initialAccumulator += v
			elif i == (days + skip - 1):
				initialAccumulator += v
				initialValue = initialAccumulator / days;
				previous = initialValue
				results.append(initialValue)
			else:
				nextValue = v * alpha + (1 - alpha) * previous;
				previous = nextValue
				results.append(nextValue)
        return results
    
    def getEMA(self, days):
        since_dt = datetime.now() - timedelta(days)
        data = self.crypto_client.fetch_ohlcv(self.market_symbol, self.timeframe, since_dt, self.limit);
        self.log(data)
        return self.calculator(days, data)

	