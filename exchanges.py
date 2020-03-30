import ccxt
import os
from dotenv import load_dotenv, find_dotenv
import sql_exchange

""" 
    dictionary of supported exchanges
    user needs to input public API key and secret for existing accounts    
"""
class Exchanges(object):
    @classmethod
    def get(cls):
        return {
            'binance': ccxt.binance({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            'bitstamp': ccxt.bitstamp({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            'bittrex': ccxt.bittrex({
                'apiKey': os.environ.get("BITTREX_KEY"),
                'secret': os.environ.get("BITTREX_SECRET"),
            }),
            'gdax': ccxt.gdax({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            'hitbtc': ccxt.hitbtc({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            'kraken': ccxt.kraken({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            'liqui': ccxt.liqui({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            'poloniex': ccxt.poloniex({
                'apiKey': 'YOUR_PUBLIC_API_KEY',
                'secret': 'YOUR_SECRET_PRIVATE_KEY',
            }),
            # add additional supported exchanges
        }
    
    @classmethod
    def sql_exchange(cls, portfolio_name):
        return sql_exchange.SqlExchange(portfolio_name)
