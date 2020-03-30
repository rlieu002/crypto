# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from models import *
from peewee import *
import crypto
from decimal import *

class SqlExchange:
    """Sql Exchange interacts with Mysql"""

    def __init__(self, portfolio_name):
        self.trade_fee = Decimal(0.0025)
        self.crypto_client = crypto.Crypto(None, 'bittrex') # defaults to using Bittrex client for looking up exchange rates to USDT
        self.init_logger()
        self.portfolio, _created = Portfolio.get_or_create(name = portfolio_name)
        self.log("Using portfolio %s (%s) " % (self.portfolio.name, self.portfolio.id))

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

    # @param currency <String> eg. BTC
    # @param base_currency <String> eg. USD
    def create_trade(self, currency, base_currency, price, quantity, trade_fee=None, comment=None, linked_trade=None, order_id=None):
        if base_currency:
            base_currency_usd = self.currency_to_usd(base_currency)
        else:
            base_currency_usd = self.currency_to_usd(currency)
            
        return Trade.create(
            portfolio = self.portfolio,
            currency = currency,
            base_currency = base_currency,
            base_currency_usd = base_currency_usd,
            price = price,
            quantity = quantity,
            trade_fee = trade_fee,
            comment = comment,
            linked_trade = linked_trade,
            order_id = order_id)

    # @param order_type is 'buy' or 'sell'
    def create_order(self, order_type, currency, base_currency, price, quantity, status):
        return Order.create(
            portfolio = self.portfolio,
            order_type = order_type,
            currency = currency,
            base_currency = base_currency,
            price = price,
            quantity = quantity,
            status = status)

    def currency_to_usd(self, currency):
        if currency == "USD":
            return 1
        else:
            base_currency = "USDT"
            return self.get_market_last_price(currency, base_currency) 
    
    def get_market_last_price(self, currency, base_currency):
        market_symbol = "%s/%s" % (currency, base_currency)
        summary = self.crypto_client.get_market_summary(market_symbol)
        return summary["last_price"]

    # @param currency <String> eg. BTC
    def check_balance(self, currency):
        balance = Trade.select(fn.Sum(Trade.quantity).alias("total")).where(
            Trade.currency == currency, 
            Trade.portfolio == self.portfolio
            ).get().total or Decimal(0.0)
        # subtract any open buy/sell orders
        open_buy_balance = Order.select(fn.Sum(Order.quantity * Order.price).alias("total")).where(
            Order.base_currency == currency,
            Order.status == 'open',
            Order.portfolio == self.portfolio,
            Order.order_type == 'buy'
        ).get().total or Decimal(0.0)
        open_sell_balance = Order.select(fn.Sum(Order.quantity).alias("total")).where(
            Order.currency == currency,
            Order.status == 'open',
            Order.portfolio == self.portfolio,
            Order.order_type == 'sell'
        ).get().total or Decimal(0.0)

        remaining = balance - open_buy_balance - open_sell_balance
        # self.log("Remaining (%s) = balance (%s) - open_buy_balance (%s) - open_sell_balance (%s)" % (remaining, balance, open_buy_balance, open_sell_balance))
        return (balance - open_buy_balance - open_sell_balance)
        
    def limit_buy_order(self, currency, base_currency, price, quantity):          
        if self.sufficient_buy_balance(currency, base_currency, quantity) == False:
            return False

        last_price = self.get_market_last_price(currency, base_currency)
        if price >= last_price:
            return self.buy_currency(currency, base_currency, last_price, quantity)
        else:
            return self.create_order('buy', currency, base_currency, price, quantity, status='open')

    def limit_sell_order(self, currency, base_currency, price, quantity):
        if self.sufficient_sell_balance(currency, base_currency, quantity) == False:
            return False

        last_price = self.get_market_last_price(currency, base_currency)
        if price <= last_price:
            return self.sell_currency(currency, base_currency, last_price, quantity)
        else:
            return self.create_order('sell', currency, base_currency, price, quantity, status='open')

    # buy currency and sell base_currency in mysql
    def buy_currency(self, currency, base_currency, price, quantity, order_id=None):
        if price:
            price = Decimal(price)
        if quantity:
            quantity = Decimal(quantity)

        total = price * quantity

        if self.sufficient_buy_balance(currency, base_currency, total) == False:
            self.log("Cannot buy currency. Insufficient balance")
            return False

        # calculate quantity after trade fees
        actual_quantity = quantity * (1 - self.trade_fee)
        trade_fee = self.trade_fee * total

        with db.transaction():
            # sell base_currency
            comment = "Sell for %s" % (currency)
            sell = self.create_trade(base_currency, None, None, -total, None, comment, None, order_id)
            # buy currency
            buy = self.create_trade(currency, base_currency, price, actual_quantity, trade_fee, None, sell, order_id)
            sell.linked_trade = buy
            sell.save()
        return buy

    # sell currency and buy base_currency in mysql
    def sell_currency(self, currency, base_currency, price, quantity, order_id=None):
        if price:
            price = Decimal(price)
        if quantity:
            quantity = Decimal(quantity)
            
        if self.sufficient_sell_balance(currency, base_currency, quantity) == False:
            return False

        # calculate quantity after trade fees
        actual_quantity = quantity * (1 - self.trade_fee)
        total = price * actual_quantity
        trade_fee = self.trade_fee * price * quantity # dont use actual quantity

        with db.transaction():
            # sell currency
            sell = self.create_trade(currency, base_currency, price, -quantity, trade_fee, None, None, order_id)
            # buy base_currency
            comment = "Buy for %s" % (currency)
            buy = self.create_trade(base_currency, None, None, total, None, comment, sell, order_id)
            sell.linked_trade = buy
            sell.save()
        return sell
    
    # check if enough base_currency to buy currency with
    def sufficient_buy_balance(self, currency, base_currency, quantity):
        base_balance = self.check_balance(base_currency)
        if base_balance < Decimal(quantity):
            self.log("Insufficient funds: Cannot buy %s/%s - Balance of %s less than %s (requested qty)" % (currency, base_currency, base_balance, quantity))
            return False
        return True

    # check if enough currency to sell
    def sufficient_sell_balance(self, currency, base_currency, quantity):
        currency_balance = self.check_balance(currency)
        if currency_balance < Decimal(quantity):
            self.log("Insufficient funds: Cannot sell %s/%s - Balance of %s less than %s (requested qty)" % (currency, base_currency, currency_balance, quantity))
            return False
        return True

    def name(self):
        return "Sql Exchange"

    ## Delegate some methods to the real exchange
    def fetch_ticker(self, market_symbol):
        return self.crypto_client.exchange.fetch_ticker(market_symbol)

    def load_markets(self):
        return self.crypto_client.exchange.load_markets()

    def fetch_ohlcv(self, market_symbol, timeframe, ms_from_epoch, limit):
        return self.crypto_client.exchange.fetch_ohlcv(market_symbol, timeframe, ms_from_epoch, limit)

    # @return [Dict] {coin: balance}
    def fetch_balance(self):
        all_coins = Trade.select(fn.Distinct(Trade.currency).alias("coin_name")).where(Trade.portfolio == self.portfolio)
        coins = map((lambda coin: coin.coin_name), all_coins)
        balances = map(self.check_balance, coins)
        return dict(zip(coins, balances))

    def create_limit_buy_order(self, market_symbol, quantity, price):
        currency, base_currency = market_symbol.split("/")
        return self.limit_buy_order(currency, base_currency, price, quantity)

    def create_limit_sell_order(self, market_symbol, quantity, price):
        currency, base_currency = market_symbol.split("/")
        return self.limit_sell_order(currency, base_currency, price, quantity)