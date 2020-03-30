# How to run:


1. installed pipenv to manage dependencies (https://docs.pipenv.org/)

2. Run `pipenv install` - will install all dependencies in a virtual environment



# Run CkryptoBot:
`pipenv run python ckrypto_bot.py`


# Run Sample calls in console: `pipenv run python`
```
from crypto import Crypto

# No simulation:
c = Crypto()


# fetch ohlcv for date
c.fetch_ohlcv("XRP/BTC", '1d', None, 1)

# check BTC balance of coin
c.check_balance('BTC')

# check market for arbitrage
c.run_check_arbitrage("TRX/BTC")

# Won't do anything in test mode
c.limit_sell_order("XRP/BTC", 20, 1.0)
c.limit_buy_order("XRP/BTC", 1.0, 0.00001)
c.buy_sell_bot("XRP/BTC", 0.5, 0.00001)
c.buy_sell_bot("XRP/BTC", 0.5, 0.00001, 0.2, 2, 0)
c.get_real_market_summary('XRP/BTC')

c.get_market_summary('XRP/BTC')
```


# Run simulation for coin on certain date in console: `pipenv run python`
```
from crypto import Crypto

coin = "NXS/BTC"
days_ago = 2
Crypto.run_simulation(coin, days_ago)
```

# Run simulated exchange in console: `pipenv run python`
```
from sql_exchange import SqlExchange

portfolio_name = "awtest"
s = SqlExchange(portfolio_name)

s.check_balance("BTC")
s.fetch_balance()
# Add 1 BTC to account
s.create_trade("BTC", "USD", 15000, 1)

s.limit_buy_order('LTC', 'BTC', 0.001, 10)
buy = s.buy_currency('NEO', "BTC", 0.013, 2)

# Deploying
`pipenv run fab deploy`
```

# Run simulated exchange in console: `pipenv run python`
```
from sql_exchange import SqlExchange

portfolio_name = "awtest"
s = SqlExchange(portfolio_name)

# Buy ETH with 1 BTC @ 0.1 ETH/BTC
s.limit_buy_order("LTC/BTC", 1.0, 0.014)

```

# Run the order_engine from console: `pipenv run python`
```
from order_engine import *
o = OrderEngine()
o.run()
```
