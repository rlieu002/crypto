# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from models import *
import crypto
from sql_exchange import SqlExchange


# OrderEngine is run on cron. 
# Every 5 minutes, it will:
# 1. check for any open orders
# 2. check prices for those open orders on real exchange
# 3. fulfill any orders if order price satisfies market price
#    1. in a transaction, create a Trade, and update status of Order to complete
class OrderEngine:

    def __init__(self):
        self.cached_open_orders = None # memoize
        self.cached_unique_currencies = None # Set
        self.crypto_client = crypto.Crypto(None, 'bittrex') # defaults to using Bittrex client
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

    # main method to execute order_engine logic
    def run(self):
        currency_prices = self.market_prices()
        trades = 0
        for order in self.open_orders():
            market_symbol = order.market_symbol()
            market_price = currency_prices[market_symbol]
            if self.price_within_range(order, market_price):
                if self.create_trade(order):
                    self.log(
                        "TRADE CREATED: Order [%d] (order price %s). Market price (%s) within range for %s" % 
                        (order.id, order.price, market_price, market_symbol))
                    trades += 1
                else:
                    self.log(
                        "ERROR CREATING TRADE: Order [%d] (order price %s). Market price (%s) within range for %s" % 
                        (order.id, order.price, market_price, market_symbol))

            else:
                # skip order
                self.log(
                    "SKIPPING: Order [%d] (order price %s). Market price (%s) not within range for %s" % 
                    (order.id, order.price, market_price, market_symbol))
        self.log("OrderEngine created %s trades" % (trades))
        return trades
        
    # Checks that market_prices satisfies this order.price
    # for buy order: order.price <= market_price
    # for sell order: order.price >= market_price
    def price_within_range(self, order, market_price):
        if order.order_type == "buy":
            return order.price >= market_price
        else:
            return order.price <= market_price


    # @return <Array> of open orders
    def open_orders(self):
        if self.cached_open_orders:
            return self.cached_open_orders

        self.cached_open_orders = Order.select().where(
            Order.status == 'open',
        )
        return self.cached_open_orders

    # @param <Iterable> orders
    # @return <Set> of unique market_symbols (eg. NEO/BTC)
    def unique_currencies(self):  
        if self.cached_unique_currencies:
            return self.cached_unique_currencies

        self.cached_unique_currencies = set()
        for order in self.open_orders():
            self.cached_unique_currencies.add(order.market_symbol())
        return self.cached_unique_currencies
        
    # return <Dict> {market_symbol<String>: market_price <Decimal>} 
    def market_prices(self):
        prices = {}
        for market_symbol in self.unique_currencies():
            prices[market_symbol] = self.crypto_client.get_market_summary(market_symbol)["last_price"]
        return prices
    
    # Creates trade for the order
    def create_trade(self, order):
        current_prices = self.market_prices()
        market_price = current_prices[order.market_symbol()]
        sql_ex = SqlExchange(order.portfolio.name)
        with db.transaction():
            if order.order_type == "buy":
                # buy_price is minimum of order.price and market_price
                buy_price = min(market_price, order.price) 
                trade = sql_ex.buy_currency(order.currency, order.base_currency, buy_price, order.quantity, order.id)
            else:
                # sell_price is higher of order.price and market_price
                sell_price = max(market_price, order.price)
                trade = sql_ex.sell_currency(order.currency, order.base_currency, sell_price, order.quantity, order.id)
            order.status = "closed"
            order.save()

        return trade


