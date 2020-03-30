# -*- coding: utf-8 -*-

import ccxt
import sys
import random
import logging
import os
import calendar
import time

from datetime import datetime, timedelta
from time import sleep
from retrying import retry
from os.path import join, dirname
from dotenv import load_dotenv, find_dotenv
from exchanges import Exchanges
from portfolio import Portfolio, Trade
from peewee import *

class Crypto:
    """Main crypto class"""

    def __init__(self, simulation_date = None, exchange = 'bittrex'):
        self.exchanges = Exchanges.get()
        self.exchange = self.exchanges[exchange]
        self.transfer_fee = 0.01
        self.trade_fee = 0.0025
        self.test_mode = True # True = does not perform trades
        self.init_logger()
        # Simulation
        self.simulation_date = None
        if simulation_date:
            self.simulation_date = simulation_date

    @staticmethod
    # @param prepump_buffer - defaults to 0, meaning don't check the prepump buffer
    def run_simulation(coin, days_ago, chunk = 0.5, profit = 0.05, buy_limit_pct = 0.00001, prepump_buffer = 0):
        simulation_date = datetime.now() - timedelta(days_ago)
        check_date = simulation_date + timedelta(1) # check date defaults to 1 day after the simulation date

        c = Crypto(simulation_date)
        buy_sell_result = c.buy_sell_bot(coin, chunk, buy_limit_pct, profit, 2, prepump_buffer)
        # Check on the prices the next day, to see if sell-orders would have gone through
        check_result = c.get_simulated_market_summary(coin, check_date)

        ## Report:
        sell_quantity = buy_sell_result['sell_quantity']
        ask_price = check_result['ask_price']
        buy_chunk = buy_sell_result['buy_chunk']
        total_sold = 0

        for price in buy_sell_result['sell_prices']:
            price = float(price)
            if price <= ask_price:
                total_sold += (sell_quantity * price)
                c.log("SOLD FOR GAIN: %s qty at price %s" % (sell_quantity, price))
            else:
                total_sold += (sell_quantity * ask_price)
                c.log("SOLD FOR LOSS: %s qty at price %s" % (sell_quantity, ask_price))

        c.log("Total Sold: %s" % (total_sold))
        c.log("Total Gain/Loss: %s (%0.2f %%)" % ((total_sold - buy_chunk), (total_sold - buy_chunk)*100/buy_chunk))
        # Return log buffer to print out etc
        return c.log_buffer

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
    
    def log(self, msg):
        prefix = ""
        if self.test_mode:
            prefix += "[TEST MODE] " 
        if self.simulation_date:
            prefix += ("<SimulationDate: %s> " % (self.simulation_date))

        msg = prefix + str(msg)
        print(msg)
        self.log_buffer.append(msg)
        self.logger.info(msg)

    # Computes expected value of arbitrage for given market
    # @param market: LTC/BTC
    def run_check_arbitrage(self, market, max_attempts = 2):
        unit_gain = 0.001
        self.log("Checking for %s arbitrage." % (market))
        self.log("Parameters: {'Unit Gain': %s}" % (unit_gain))

        attempts = 1
        while attempts <= max_attempts:
            self.log("Attempt: %s of %s" % (attempts, max_attempts))
            res = self.expected_value(market, unit_gain)
            if res:
                self.log("Arbitrage Opportunity Discovered!")
                self.log(res)
                break
            attempts += 1
            sleep(10)

    # Prints list of prepumped markets and runs expected value for arbitrage
    def run_prepump(self):
        prepumped_markets = self.find_prepumped_markets()
        self.log("Pre-pumped markets on %s:" % (self.exchange.name))
        self.log(prepumped_markets)
        unit_gain = 0.05
        hits = []
        
        # Just test on 10 ranodm markets
        # sample_size = 10
        # prepumped_markets = self.random_sample(prepumped_markets, sample_size)
        # self.log("Testing: sampling %s markets: " % (sample_size))
        # self.log(prepumped_markets)
        
        for market in prepumped_markets:
            self.log("Testing market %s for arbitrage" % (market))
            
            result = self.expected_value(market, unit_gain)
            if result:
                self.log("- HIT!")
                hits.append(result)
            else:
                self.log("- None")
            sleep(1)
            
        self.log("HITS !!!!!!!!")
        self.log("Number of hits: ", len(hits))
        self.log(hits)

    # Prints list of any dumped markets and runs buy_sell_bot
    def run_dump(self, days_ago, chunk, percent_increase, profit, splits, prepump_buffer, portfolio_id):
        dumped_markets = self.find_dumped_markets(days_ago)
        self.log("Dumped markets on %s:" % (self.exchange.name))
        self.log(dumped_markets)
        unit_gain = 0.05
        hits = []

        for market in dumped_markets:
            self.log("Testing market %s for arbitrage" % (market))
            
            result = self.buy_sell_bot(market, days_ago, chunk, percent_increase, profit, splits, prepump_buffer, portfolio_id)
            if result:
                self.log("- HIT!")
                hits.append(result)
            else:
                self.log("- None")
            sleep(1)
            
    def fetch_markets(self, symbol):
        prices = {}
        exchanges = self.exchanges
        
        # pull prices of coin across exchanges
        for key in exchanges:
            try:
                market_info = exchanges[key].fetch_ticker(symbol)
            except:
                continue
        
            market_bid = market_info["bid"]
            market_ask = market_info["ask"]
        
            # Ignore when None
            if (market_bid is None) or (market_ask is None):
                continue
            
            prices.setdefault("bid", {})
            prices.setdefault("ask", {})            
            prices["bid"][key] = market_bid
            prices["ask"][key] = market_ask
        return prices    

    # check if price variance is greater than cost
    def expected_value(self, market_symbol, unit_gain):
        prices = self.fetch_markets(market_symbol)
        bid_prices = prices["bid"]
        ask_prices = prices["ask"]
    
        # select exchanges with highest bid and lowest ask
        high_bid_exchange = max(bid_prices, key=(lambda key: bid_prices[key]))
        high_bid = bid_prices[high_bid_exchange]
        # self.log("BID PRICES: ")
        # self.log(bid_prices)
        # self.log("High bid: %s on %s" % (high_bid, high_bid_exchange))
        low_ask_exchange = min(ask_prices, key=(lambda key: ask_prices[key]))
        low_ask = ask_prices[low_ask_exchange]
        # self.log("ASK PRICES: ")
        # self.log(ask_prices)
        # self.log("low ask: %s on %s" % (low_ask, low_ask_exchange))
        # take difference of prices
        difference = high_bid - low_ask
        costs = (low_ask * self.trade_fee) + (low_ask * self.transfer_fee) + (high_bid * self.trade_fee)
        self.log("%s (bid-ask) - %s (costs) = %s (profit)" % (difference, costs, difference - costs))
        # see if difference is greater than transfer fees + trade fees
        if difference > costs:
            # price_risk = # figure out through trial and error
            # calculate expected value:
            # expected_value = difference - ((high_bid * transfer_fee) + (low_ask * trade_fee) + price_risk)
            # while expected value is positive:
            if (difference - costs) > (unit_gain * low_ask):
                return {
                    "market": market_symbol, 
                    "high_bid_exchange": high_bid_exchange, 
                    "low_ask_exchange": low_ask_exchange,
                    "high_bid": high_bid,
                    "low_ask": low_ask,
                    "costs": costs,
                    "difference": difference
                }
        return False

    # Returns n elements from mylist, randomly sampled
    def random_sample(self, mylist, n):
        return [ mylist[i] for i in sorted(random.sample(xrange(len(mylist)), n)) ]

    # Returns simulated summary based on historic data
    def get_simulated_market_summary(self, market_symbol, datetime):
        dt, o, h, l, c, v = self.fetch_ohlcv(market_symbol, '1d', datetime, 1)[0]
        self.log("get_simulated_market_summary for %s using date %s" % (market_symbol, dt))
        summary = {
            "low_24_hr": l,
            "last_price": o,
            "ask_price": o,
            "close": c,
            "volume": v,
        }
        self.log(summary)
        return summary

    def get_real_market_summary(self, market_symbol):
        summary = self.exchange.fetch_ticker(market_symbol)
        self.log("get_real_market_summary for %s" % (market_symbol))
        summary = {
            "low_24_hr": summary["low"],
			"high_24_hr": summary["high"],
            "last_price": summary["last"],
            "ask_price": summary["ask"],
			# baseVolume is volume of current ALT coin
			# quoteVolume / current price
            "volume": summary["baseVolume"],
			# quoteVolume is a volume of current coin in terms of exchange currency
		    # EX:  edg/btc base = 23812831.212 (edg), quote = 242.31 (btc)
            "quoteVolume": summary["quoteVolume"],
            "change": summary["change"],
        }
        self.log(summary)
        return summary

    # @param market_symbol <String> eg. XRP/BTC
    def get_market_summary(self, market_symbol):
        if self.simulation_date:
            return self.get_simulated_market_summary(market_symbol, self.simulation_date)
        else:
            return self.get_real_market_summary(market_symbol)
    
    # Finds markets that are pre-pumped
    def find_prepumped_markets(self, prepump_buffer = 0.1):
        exchange_markets = self.exchange.load_markets()
        goodMarkets = []
        for market_symbol in exchange_markets:
            currency = exchange_markets[market_symbol]["info"]["MarketCurrencyLong"]
            base_currency = exchange_markets[market_symbol]["info"]["BaseCurrency"]
            self.log("Finding details on: %s" % (market_symbol))
            if exchange_markets[market_symbol]["active"] and base_currency == "BTC" and self.coin_prepumped(market_symbol, prepump_buffer):
                goodMarkets.append(market_symbol)
        return goodMarkets
    
    # Return True if market is pre-pumped or volume is too high
    # retry with random wait betwen 1-2s
    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000) 
    def coin_prepumped(self, market_symbol, prepump_buffer = 0.1):
        summary = self.get_market_summary(market_symbol)
        # last_price is smaller than 50% increase since yerterday
        if summary["volume"] < 100 and summary["last_price"] < (1.0 + prepump_buffer) * summary["low_24_hr"]:
            return False
        else:
            return True

    # Finds markets that are dumped
    def find_dumped_markets(self, days_ago = 1, dump_buffer = 0.1):
        exchange_markets = self.exchange.load_markets()
        goodMarkets = []
        for market_symbol in exchange_markets:
            currency = exchange_markets[market_symbol]["info"]["MarketCurrencyLong"]
            base_currency = exchange_markets[market_symbol]["info"]["BaseCurrency"]
            self.log("Finding details on: %s" % (market_symbol))
            if exchange_markets[market_symbol]["active"] and base_currency == "BTC" and self.coin_dumped(market_symbol, days_ago, dump_buffer):
                goodMarkets.append(market_symbol)
        return goodMarkets

    # Return True if market is dumped and volume is significant
    # retry with random wait betwen 1-2s
    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000) 
    def coin_dumped(self, market_symbol, days_ago = 1, dump_buffer = 0.1):
        check_date = datetime.now() - timedelta(days_ago + 1)
        check_date2 = datetime.now() - timedelta(days_ago)
        summary = self.get_simulated_market_summary(market_symbol, check_date)
        summary2 = self.get_simulated_market_summary(market_symbol, check_date2)
        # change is greater than 10% decrease since yesterday and quoteVolume > 1000
        if ((summary2["close"] / summary["close"]) - 1.0) < -dump_buffer and summary["volume"] > 1000:
            return True
        else:
            return False
    
    # @param market_symbol <String> eg. XRP/BTC
    # @param chunk <Float> Amount of the base currency to buy with (usually btc)
    # @param percent_increase <Float> % increase to set the limit buy price
    # @param profit <Float> SELL_PRICE = (1.0 + profit) * BUY_PRICE
    # @param splits <Int> how many times to initiate sells of (profit) % increase
    # @param prepump_buffer <Float> allowed prepump % increase from the "last 24 hr low price"
    # @param trade_fee <Float> % fee for trades
    def buy_sell_bot(self, market_symbol, days_ago, chunk, percent_increase = 0.05, profit = 0.1, splits = 2, prepump_buffer = 0.5, trade_fee = 0.0025, portfolio_id = 1):
        message = "buy_sell_bot parameters: %s (market_symbol), %s (chunk), %s (percent_increase), %s (profit), %s (splits), %s (prepump_buffer)" % (market_symbol, chunk, percent_increase, profit, splits, prepump_buffer)
        self.log(message)

        buy_currency, base_currency = market_symbol.split("/")

        # if prepump_buffer > 0 and self.coin_prepumped(market_symbol, prepump_buffer):
        #     self.log("Exiting. Market (%s) is pre-pumped" % (market_symbol))
        #     self.log("If you're sure, set the prepump_buffer (%s) to 0, then re-run" % (prepump_buffer))
        #     return False
        
        summary = self.get_market_summary(market_symbol)
        buy_price = summary["last_price"] * (1.0 + percent_increase)
        buy_units = chunk/buy_price

        sell_prices = [ ( buy_price * ((profit + 1)**(i+1)) ) for i in range(0,splits) ]
        sell_quantity = buy_units/float(splits)
        sell_totals = [ (sell_price * sell_quantity) for sell_price in sell_prices ]
        sum_sells = sum(sell_totals)
        total_gain = sum_sells - chunk

        # 8 decimal places
        sell_prices = [ ("%.8f" % sell_price) for sell_price in sell_prices ]

        message = "buy_sell_bot will buy %s units %s with %s %s (chunk) at limit price %s" % (buy_units, market_symbol, chunk, base_currency, buy_price)
        self.log(message)
        message = "buy_sell_bot will open %s sell orders of qty %s. Sell prices: %s -> %s" % (splits, sell_quantity, ','.join(map(str, sell_prices)), ','.join(map(str, sell_totals)))
        self.log(message)
        message = "buy_sell_bot if all sold, TOTAL GAIN will be: %s - %s = %s %s" % (sum_sells, chunk, total_gain, base_currency)
        self.log(message)

        # if self.test_mode:
        #     return {
        #         "market_symbol": market_symbol,
        #         "sum_sells": sum_sells,
        #         "buy_chunk": chunk,
        #         "buy_units": buy_units,
        #         "buy_price": buy_price,
        #         "total_gain": total_gain,
        #         "sell_prices": sell_prices,
        #         "sell_quantity": sell_quantity,
        #         "sell_totals": sell_totals,
        #         "splits": splits,
        #     }

        buy_order = self.limit_buy_order(market_symbol, chunk, buy_price, trade_fee, portfolio_id)
        orders = []
        if buy_order:
            orders.append(buy_order)
            check_date = datetime.now() - timedelta(days_ago - 1)
            summary = self.get_simulated_market_summary(market_symbol, check_date)
            for sell_price in sell_prices:
                message = "buy_sell_bot will open sell order for %s -> %s (quantity) * %s (price)" % (market_symbol, sell_quantity, sell_price)
                self.log(message)
                if summary["close"] > sell_price:
                    sell_order = self.limit_sell_order(market_symbol, sell_quantity, sell_price, trade_fee, portfolio_id)
                    if sell_order:
                        orders.append(sell_order)
            return orders
        return False    

    # https://github.com/ccxt/ccxt/wiki/Manual#api-methods--endpoints
    # @param coin <String> eg. BTC
    def check_balance(self, currency, portfolio_id = 1):
        if self.test_mode:
            balance = Trade.select(fn.Sum('quantity')).where(Trade.currency == currency, Trade.portfolio_id == portfolio_id).first()
            self.log("%s balance: %s" % (currency, balance))
            return balance

        balance = self.exchange.fetch_balance()
        # print balance
        free = balance.get("free", {}).get(coin, 0.0)
        self.log("check_balance for coin %s: %s (free)" % (coin, free))
        return free

    # create portfolio in mysql
    def create_portfolio(self, name):
        Portfolio.create(
            name = name,
            created_at = datetime.now(),
            updated_at = datetime.now()
        )
    
    # create trade in mysql
    def create_trade(self, currency, base_currency, base_currency_usd, price, quantity, portfolio_id = 1):
        Trade.create(
            portfolio_id = portfolio_id,
            currency = currency,
            base_currency = base_currency,
            base_currency_usd = base_currency_usd,
            price = price,
            quantity = quantity,
            created_at = datetime.now(),
            updated_at = datetime.now()
        )

    # buy currency and sell base_currency in mysql
    def buy_currency(self, currency, base_currency, price, quantity, trade_fee = 0.0025, portfolio_id = 1):
        # check if enough base_currency to buy currency with
        base_balance = self.check_balance(base_currency, portfolio_id)
        if base_balance <= 0.0:
            self.log("buy_order failed: Balance of %s <= 0" % (base_currency))
            return False
        # sell base_currency
        market_symbol = "%s/USDT" % (base_currency)
        summary = self.get_market_summary(market_symbol)
        base_currency_usd = summary["last_price"]
        currency_usd = base_currency_usd * price
        total = price * quantity
        self.create_trade(base_currency, currency, currency_usd, base_currency_usd, -total, portfolio_id)
        # calculate quantity after trade fees
        actual_quantity = quantity * (1.0 - trade_fee)
        # buy currency
        order = self.create_trade(currency, base_currency, base_currency_usd, price, actual_quantity, portfolio_id)
        return order

    # sell currency and buy base_currency in mysql
    def sell_currency(self, currency, base_currency, price, quantity, trade_fee = 0.0025, portfolio_id = 1):
        # check if enough currency to sell
        currency_balance = self.check_balance(currency, portfolio_id)
        if currency_balance <= 0.0:
            self.log("sell_order failed: Balance of %s <= 0" % (currency))
            return False
        # sell currency
        market_symbol = "%s/USDT" % (base_currency)
        summary = self.get_market_summary(market_symbol)
        base_currency_usd = summary["last_price"]
        self.create_trade(currency, base_currency, base_currency_usd, price, -quantity, portfolio_id)
        # calculate quantity after trade fees
        actual_quantity = quantity * (1.0 - trade_fee)
        total = price * actual_quantity
        # buy base_currency
        order = self.create_trade(base_currency, base_currency, base_currency_usd, price, total, portfolio_id)
        return order

    # limit buy will buy at price or lower
    # @param market_symbol <String> eg. XRP/BTC
    # @param chunk <Float> the amount in the base currency (usually BTC)
    # @param price <Float> limit price to purchase the currency
    # @return order if successful or False if unsuccessful
    def limit_buy_order(self, market_symbol, chunk, price, trade_fee = 0.0025, portfolio_id = 1):
        # eg. ETH/BTC
        buy_currency, base_currency = market_symbol.split("/")
        quantity = chunk / price 
        total_cost = quantity * price
        self.log("limit_buy_order for %s" % (market_symbol))
        self.log("chunk: %s of %s" % (chunk, base_currency))
        self.log("%s (qty) * %s (price) = %s (total)" % (quantity, price, total_cost))

        if self.test_mode: 
            self.log("Test mode: only impacts simulated portfolio")
            order = self.buy_currency(buy_currency, base_currency, price, quantity, trade_fee, portfolio_id)
            return order

        order = self.exchange.create_limit_buy_order(market_symbol, quantity, trade_fee, price)
        if order:
            self.log("limit_buy_order success")
            self.log(order)
            return order
        else:
            self.log("limit_buy_order failed")
            return False

    # limit sell will sell at price or higher
    # @param market_symbol <String> eg. XRP/BTC
    # @param quantity <Float> the amount of currency to sell
    # @param price <Float> limit price to sell the currency
    # @return order if successful or False if unsuccessful
    def limit_sell_order(self, market_symbol, quantity, price, trade_fee = 0.0025, portfolio_id = 1):
        # eg. ETH/BTC
        sell_currency, base_currency = market_symbol.split("/")
        total_cost = quantity * price
        self.log("limit_sell_order for %s" % (market_symbol))
        self.log("%s (qty) * %s (price) = %s (total)" % (quantity, price, total_cost))

        if self.test_mode: 
            self.log("Test mode: only impacts simulated portfolio")
            order = self.sell_currency(sell_currency, base_currency, price, quantity, trade_fee, portfolio_id)
            return order

        order = self.exchange.create_limit_sell_order(market_symbol, quantity, trade_fee, price)
        if order:
            self.log("limit_sell_order success")
            self.log(order)
            return order
        else:
            self.log("limit_sell_order failed")
            return False

    # fetchOHLCV (symbol, timeframe = '1m', since = undefined, limit = undefined, params = {})    
    #  [
    #     1504541580000, // UTC timestamp in milliseconds
    #     4235.4,        // (O)pen price
    #     4240.6,        // (H)ighest price
    #     4230.0,        // (L)owest price
    #     4230.7,        // (C)losing price
    #     37.72941911    // (V)olume
    # ]
    def fetch_ohlcv(self, market_symbol, timeframe = '1d', since = None, limit = None):
        days_ago = 1
        yesterday = datetime.now() - timedelta(days_ago)
        since_dt = since or yesterday
        ms_from_epoch = self.datetime_to_ms_from_epoch(since_dt)

        results = self.exchange.fetch_ohlcv(market_symbol, timeframe, ms_from_epoch, limit)
        for res in results:
            res[0] = self.ms_from_epoch_to_datetime(res[0])
        return results

    def datetime_to_ms_from_epoch(self, datetime):
        epoch = datetime.utcfromtimestamp(0)
        return int((datetime - epoch).total_seconds()) * 1000.0

    def ms_from_epoch_to_datetime(self, ms_from_epoch):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ms_from_epoch / 1000))

