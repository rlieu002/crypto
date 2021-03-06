import ccxt
import sys
import random

from time import sleep
from retrying import retry

class Crypto:
    # dictionary of supported exchanges
    # user needs to input public API key and secret for existing accounts
    exchanges = { 
        'binance': ccxt.binance({ 
            'apiKey': 'YOUR_PUBLIC_API_KEY',
            'secret': 'YOUR_SECRET_PRIVATE_KEY',
        }),
        'bitstamp': ccxt.bitstamp({ 
            'apiKey': 'YOUR_PUBLIC_API_KEY',
            'secret': 'YOUR_SECRET_PRIVATE_KEY',
        }),
        'bittrex': ccxt.bittrex({ 
            'apiKey': 'YOUR_PUBLIC_API_KEY',
            'secret': 'YOUR_SECRET_PRIVATE_KEY',
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
    
    def __init__(self, exchange = 'bittrex'):
        self.exchange = self.exchanges[exchange]
    
    def run_prepump(self):
        prepumped_markets = self.find_prepumped_markets()
        print "Pre-pumped markets on %s:" % (self.exchange.name)
        print prepumped_markets
        
        hits = []
        
        # Just test on 10 ranodm markets
        sample_size = 10
        prepumped_markets = self.random_sample(prepumped_markets, sample_size)
        print "Testing: sampling %s markets: " % (sample_size)
        print prepumped_markets
        
        for market in prepumped_markets:
            print "Testing market %s for arbitrage" % (market)
            
            result = self.expected_value(market, 0.05, 0.01, 0.0025)
            if result:
                print "- HIT!"
                hits.append(result)
            else:
                print "- None"    
            sleep(1)
            
        print "HITS !!!!!!!!"
        print "Number of hits: ", len(hits)
        print hits
            
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
def expected_value(self, market_symbol, unit_gain, transfer_fee, trade_fee):
    # get btc denominated coin prices
    coin_prices = self.fetch_markets(market_symbol)
    if not coin_prices:
        return False
    # coin_bids = coin_prices["bid"]
    coin_asks = coin_prices["ask"]
    # select exchange with lowest ask
    low_ask_exchange = min(coin_asks, key=(lambda key: coin_asks[key]))
    low_ask = coin_asks[low_ask_exchange]

    # get eth denominated coin prices
    currencies = market_symbol.split("/")
    market_symbol_eth = currencies[0]+"/ETH"
    coin_prices_eth = self.fetch_markets(market_symbol_eth)
    if not coin_prices_eth:
        return False
    coin_bids_eth = coin_prices_eth["bid"]
    # coin_asks_eth = coin_prices_eth["ask"]
    # select exchange with highest bid
    high_bid_exchange = max(coin_bids_eth, key=(lambda key: coin_bids_eth[key]))
    high_bid = coin_bids_eth[high_bid_exchange]

    # get eth to btc prices
    eth_prices = self.fetch_markets("ETH/BTC")
    if not eth_prices:
        return False
    eth_bids = eth_prices["bid"]
    # eth_asks = eth_prices["ask"]
    # select exchange with highest bid
    high_bid_exchange_eth = max(eth_bids, key=(lambda key: eth_bids[key]))
    high_bid_eth = eth_bids[high_bid_exchange_eth]

    # take difference of prices
    difference = (high_bid * high_bid_eth) - low_ask
    costs = (low_ask * trade_fee) + (low_ask * transfer_fee) + (high_bid * trade_fee) + (high_bid * transfer_fee) + (high_bid_eth * trade_fee)
    print "%s (bid-ask) - %s (costs) = %s (profit)" % (difference, costs, difference - costs)
    # see if difference is greater than transfer fees + trade fees
    if difference > costs:
        # price_risk = # figure out through trial and error
        # calculate expected value:
        # expected_value = difference - ((high_bid * transfer_fee) + (low_ask * trade_fee) + price_risk)
        # while expected value is positive:
        if (difference - costs) > (unit_gain * low_ask):
            return {
                "low_ask_exchange":low_ask_exchange,
                "high_bid_exchange":high_bid_exchange,
                "high_bid_exchange_eth":high_bid_exchange_eth
            }
    return False

    # Returns n elements from mylist, randomly sampled
    def random_sample(self, mylist, n):
        return [ mylist[i] for i in sorted(random.sample(xrange(len(mylist)), n)) ]
    
    def get_market_summary(self, market_symbol):
        # we assume market symbol is always in format of "COIN/BTC"
        summary = self.exchange.fetch_ticker(market_symbol)
        low_24_hr = summary["low"]
        last_price = summary["last"]
        ask_price = summary["ask"]
        volume = summary["baseVolume"]
        return [low_24_hr, last_price, ask_price, volume]
    
    # Finds markets that are pre-pumped
    def find_prepumped_markets(self, prepump_buffer = 0.5):
        exchange_markets = self.exchange.load_markets()
        goodMarkets = []
        for market_symbol in exchange_markets:
            currency = exchange_markets[market_symbol]["info"]["MarketCurrencyLong"]
            base_currency = exchange_markets[market_symbol]["info"]["BaseCurrency"]
            print "Finding details on: %s" % (market_symbol)
            if exchange_markets[market_symbol]["active"] and base_currency == "BTC" and self.coin_pumped(market_symbol, prepump_buffer):
                goodMarkets.append(market_symbol)
        return goodMarkets
    
    # Return True if market is pre-pumped
    # retry with random wait betwen 1-2s
    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000) 
    def coin_pumped(self, market_symbol, prepump_buffer = 0.5):
            low_24_hr, last_price, ask_price, volume = self.get_market_summary(market_symbol)
            if volume < 100 and last_price < (1.0 + prepump_buffer) * low_24_hr: #last_price is smaller than 50% increase since yerterday
                return False
            else:
                return True
        
        


# Main:
crypto = Crypto()
crypto.run_prepump()
