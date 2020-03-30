      
        
# ARBITRAGE
def arbitrage_bot():
    # market_symbol = market_symbol_global
    transfer_fee = 0.005
    trade_fee = 0.005
    unit_gain = 0.1 # desired gain % per unit to execute
    min_balance = 0.05 # minimum balance to initiate trade
    percent_increase = 0.05
    no_of_retries = 5
    # find coins being pumped
    exchange_markets = exchange.load_markets()
    # self.log(exchange_markets)
    markets = []
    for i in exchange_markets:
        market_symbol = exchange_markets[i]["symbol"]
        low_24_hr, last_price, ask_price, volume = get_market_summary(market_symbol)
        if volume > 100 and last_price > (1.0 + prepump_buffer) * low_24_hr: #last_price is greater than 50% increase since yerterday
            self.log("Coin is pumped")
            markets.append(market_symbol)
    # self.log((ccxt.exchanges))
    for i in markets:
        counter = 0
        while counter < no_of_retries:
            if expected_value(i, unit_gain, transfer_fee, trade_fee):
                price_info = expected_value(i, unit_gain, transfer_fee, trade_fee)
                high_bid_exchange = price_info["high_bid_exchange"]
                low_ask_exchange = price_info["low_ask_exchange"]
                # check available balance (BTC) to buy coin
                balance_details = exchanges[low_ask_exchange].fetch_balance()
                balance_btc = balance_details["BTC"]["free"]
                if balance_btc and balance_btc < min_balance:
                    # send funds to exchange with lower price
                    ask_address = # get deposit address from exchange with lower price
                    # withdraw from default exchange
                    exchange.withdraw("BTC", min_balance, ask_address)
                elif balance_btc and balance_btc > min_balance:
                    low_market_info = exchanges[low_ask_exchange].fetch_ticker(i)
                    low_last_price = low_market_info["last"]
                    market_symbol = low_market_info["symbol"]
                    currency = low_market_info["info"]["MarketCurrency"]
                    high_market_info = exchanges[high_bid_exchange].fetch_ticker(i)
                    high_last_price = high_market_info["last"]
                    # buy from exchange with lower price
                    buy_order = buy_chunk(low_last_price, market_symbol, percent_increase, min_balance)
                    self.log([buy_order, "Units Bought : %s" % (units_bought_global)])
                    # transfer to exchange with higher price
                    bid_address = # get deposit address from exchange with higher price
                    # withdraw from exchange with lower price
                    exchanges[low_ask_exchange].withdraw(currency, units_bought_global, bid_address)
                    # sell on exchange with higher price
                    balance_details = exchanges[low_ask_exchange].fetch_balance()
                    balance_currency = balance_details[currency]["free"]
                    if balance_currency and balance_currency > 0:
                        sell_order = sell_chunk(high_last_price, market_symbol, percent_increase, balance_currency)
                        self.log([sell_order, "Units Sold : %s" % (units_sold_global)])
                    # send funds to exchange with lower price
                    ask_address = # get deposit address from exchange with lower price
                    # withdraw from exchange with higher price
                    balance_details = exchanges[low_ask_exchange].fetch_balance()
                    balance_btc = balance_details["BTC"]["free"]
                    if balance_btc and balance_btc > min_balance:
                        exchanges[high_bid_exchange].withdraw("BTC", min_balance, ask_address)
            counter += 1

# method to cancel all open BTC pair orders
def cancel_all_bot():
    exchange_markets = exchange.load_markets()
    # self.log(exchange_markets)
    for i in exchange_markets:
        currency = exchange_markets[i]["info"]["MarketCurrency"]
        base_currency = exchange_markets[i]["info"]["BaseCurrency"]
        market_symbol = exchange_markets[i]["info"]["Symbol"]
        if exchange_markets[i]["info"]["IsActive"] and base_currency == "BTC":
            open_orders = exchange.fetch_open_orders(market_symbol) #get open orders
            if len(open_orders) > 0:
                self.log([market_symbol, open_orders])
                for i in open_orders:
                    exchange.cancel_order(open_orders[i]["id"]) # cancel order
                self.log("orders cancelled for %s" % (market_symbol))

# method to sell all BTC pair orders
# params- profit_rate(float)[default = 0.2] at which sell orders need to be set
def sell_all_bot(profit_rate = 0.2):
    exchange_markets = exchange.load_markets()
    expected_worth = 0.0
    for i in exchange_markets:
        currency = exchange_markets[i]["info"]["MarketCurrency"]
        base_currency = exchange_markets[i]["info"]["BaseCurrency"]
        market_symbol = exchange_markets[i]["info"]["Symbol"]
        if exchange_markets[i]["info"]["IsActive"] and base_currency == "BTC":
            balance_details = exchange.fetch_balance()
            balance = balance_details[currency]["free"]
            if balance and balance > 0.0: #purchased coins
                orders_history = exchange.fetch_orders(market_symbol)
                net_value = 0.0
                for i in orders_history:
                    if orders_history[i]["OrderType"] == "LIMIT_BUY":
                        net_value += orders_history[i]["Price"]
                    if orders_history[i]["OrderType"] == "LIMIT_SELL":
                        net_value -= orders_history[i]["Price"] 
                if net_value > 0: # buys are more, we need to get more than this net value by selling available coins
                    sell_price = (net_value + net_value*profit_rate)/balance
                  sell_price = "%.8f" % sell_price # (8 decimal places)
                    exchange.create_limit_sell_order(market_symbol, balance, sell_price)
                    self.log("order placed for %s at %s" % (market_symbol, sell_price))
                expected_worth += (net_value + net_value*profit_rate)
    self.log("Expected Worth = %s" % (expected_worth))


def buy_chunk(last_price, market_symbol, percent_increase, chunk):
    unit_price = last_price + last_price * percent_increase
    quantity = chunk/unit_price
    self.log("Purchasing coin...")
    print [{market: market_symbol, quantity: quantity, rate: unit_price}]
    order = exchange.create_limit_buy_order(market_symbol, quantity, unit_price)
    print "Success" if order and order["id"] else print "Failed"
    cnt = 1
    while cnt <= 3 and order and not order["id"]: #retry
        self.log("Retry #%s Purchasing coin..." % (cnt))
        sleep(1)
        order = exchange.create_limit_buy_order(market_symbol, quantity, unit_price)
        print "Success" if order and order["id"] else print "Failed"
        cnt += 1
    if order and order["id"]: units_bought_global = quantity 
    return order

def sell_chunk(last_price, market_symbol, percent_decrease, chunk):
    unit_price = last_price + last_price * percent_decrease
    # quantity = chunk/unit_price
    self.log("Selling coin...")
    print [{market: market_symbol, quantity: chunk, rate: unit_price}]
    order = exchange.create_limit_sell_order(market_symbol, chunk, unit_price)
    print "Success" if order and order["id"] else print "Failed"
    cnt = 1
    while cnt <= 3 and order and not order["id"]: #retry
        self.log("Retry #%s Selling coin..." % (cnt))
        sleep(1)
        order = exchange.create_limit_sell_order(market_symbol, chunk, unit_price)
        print "Success" if order and order["id"] else print "Failed"
        cnt += 1
    if order and order["id"]: units_sold_global = chunk
    return order

# method to place BUY order
# params: 
# percent_increase(float) - BUY price will be percent_increase of last_price of the market i.e BUY_PRICE = (1.0 + percent_increase)*last_price
# chunk(float) - Amount of BTC to invest for buying altcoin i.e BUY IF [last_price < (1.0 + prepump_buffer)*low_24_hr]
# prepump_buffer(float) -  Allowed buffer for prepump
def buy_bot(percent_increase = 0.05, chunk = 0.006, prepump_buffer = 0.5):
    market_symbol = market_symbol_global
    low_24_hr, last_price, ask_price, volume = get_market_summary(market_symbol)
    total_spent = 0.0
    print [low_24_hr, last_price, ask_price, volume]
    if volume < 100 and last_price < (1.0 + prepump_buffer) * low_24_hr: #last_price is smaller than 50% increase since yerterday
        self.log("Coin is not prepumped")
        order = buy_chunk(last_price, market_symbol, percent_increase, chunk)
        print([order, "Units Bought : %s" % (units_bought_global)])

# method to BUY all low volume coins
# params: 
# percent_increase(float) - BUY price will be percent_increase of last_price of the market i.e BUY_PRICE = (1.0 + percent_increase)*last_price
# chunk(float) - Amount of BTC to invest for buying altcoin i.e BUY IF [last_price < (1.0 + prepump_buffer)*low_24_hr]
# prepump_buffer(float) -  Allowed buffer for prepump
def buy_all_bot(percent_increase = 0.05, chunk = 0.006, prepump_buffer = 0.5):
    exchange_markets = exchange.load_markets()
    for i in exchange_markets:
        currency = exchange_markets[i]["info"]["MarketCurrency"]
        base_currency = exchange_markets[i]["info"]["BaseCurrency"]
        market_symbol = exchange_markets[i]["info"]["Symbol"]
        if exchange_markets[i]["IsActive"] and base_currency == "BTC":
            market_symbol_global = market_symbol
            buy_bot(percent_increase, chunk, prepump_buffer)

# method to place SELL order
# params:
# percent_decrease(float) - BUY price will be percent_decrease of last_price of the market, eg. SELL_PRICE = (1.0 - percent_decrease)*last_price
def sell_bot(percent_decrease = 0.1):
    market_symbol = market_symbol_global
    currency = currency_global
    low_24_hr, last_price, ask_price = get_market_summary(market_symbol)
    sell_price = last_price - percent_decrease*last_price
    balance_details = exchange.fetch_balance()
    balance = balance_details[currency]["free"]
    sell_price = "%.8f" % sell_price # (8 decimal places)
    if balance_details and balance and balance > 0.0:
        print [market_symbol, last_price, balance, sell_price]
        self.log("Selling coin...")
        print [{market: market_symbol, quantity: balance, rate: sell_price}]
        order = exchange.create_limit_sell_order(market_symbol, balance, sell_price)
        print "Success" if order and order["id"] else print "Failed"
        cnt = 1
        while cnt <= 3 and order and not order["id"]: #retry
            self.log("Retry #%s Selling coin..." % (cnt))
            sleep(1)
            order = exchange.create_limit_sell_order(market_symbol, balance, sell_price)
            print "Success" if order and order["id"] else print "Failed"
            cnt += 1
        self.log("order placed for %s at %s" % (market_symbol, sell_price))
    else:
        puts "Insufficient Balance"

# method to place BUY and SELL order immediately after purchase
# params :
# percent_increase(float)  ->  BUY_PRICE = (1.0 + percent_increase) * last_price
# chunk(float)  -> Amount of BTC to invest for buying altcoin
# prepump_buffer(float) -  Allowed buffer for prepump
# profit(float) -> SELL_PRICE = (1.0 + profit) * BUY_PRICE
# splits(int) -> How many splits of available quantity you want to make [profit] increment each time in next sell order
def buy_sell_bot(percent_increase = 0.05, chunk = 0.004, prepump_buffer = 0.5, profit = 0.2, splits = 2, no_of_retries = 10):
    market_symbol = market_symbol_global
    currency = currency_global
    low_24_hr, last_price, ask_price = get_market_summary(market_symbol)
    total_spent = 0.0
    print [low_24_hr, last_price, ask_price]
    if last_price < (1.0 + prepump_buffer)*low_24_hr: #last_price is smaller than 50% increase since yerterday
        order = buy_chunk(last_price, market_symbol, percent_increase, chunk)
        buy_price = last_price + last_price * percent_increase
        counter = 0
        while counter < no_of_retries:
            balance_details = exchange.fetch_balance()
            balance = balance_details[currency]["free"]
            print balance_details
            if balance_details and balance and balance > 0.0: # available coins present
                qty = balance/splits
                for i in range(0, splits):
                    if (i-1 == splits): qty += (int(balance) % splits) 
                    sell_price = buy_price + buy_price * (profit * (i+1))
                    sell_price = "%.8f" % sell_price # (8 decimal places)
                    print [market_symbol, last_price, balance, sell_price]
                    self.log("Selling coin...")
                    print [{market: market_symbol, quantity: balance, rate: sell_price}]
                    order = exchange.create_limit_sell_order(market_symbol, balance, sell_price)
                    print "Success" if order and order["id"] else print "Failed"
                    cnt = 1
                    while cnt <= 3 and order and not order["id"]: #retry
                        self.log("Retry #%s Selling coin..." % (cnt))
                        sleep(1)
                        order = exchange.create_limit_sell_order(market_symbol, balance, sell_price)
                        print "Success" if order and order["id"] else print "Failed"
                        cnt += 1
                    self.log("order placed for %s at %s" % (market_symbol, sell_price))
                break
            counter += 1
            sleep(0.5)

# method to place SELL order by cancelling all open orders
# params:
# percent_decrease(float) - BUY price will be percent_decrease of last_price of the market, eg. SELL_PRICE = (1.0 - percent_decrease)*last_price
def sell_at_any_cost(percent_decrease = 0.3):
    market_symbol = market_symbol_global
    open_orders = exchange.fetch_open_orders(market_symbol)
    #cancel all orders
    if len(open_orders) > 0:
        for i in open_orders:
            exchange.cancel_order(open_orders[i]["id"])
    # call sell bot again with lower profit
    sell_order = sell_bot(percent_decrease)
