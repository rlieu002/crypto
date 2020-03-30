# -*- coding: utf-8 -*-


"""Simple Bot to send timed Telegram messages.

# This program is dedicated to the public domain under the CC0 license.

This Bot uses the Updater class to handle the bot and the JobQueue to send
timed messages.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Alarm Bot example, sends a message after a set time.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
from crypto import Crypto
from telegram.ext import Updater, CommandHandler
import logging
import os
from dotenv import load_dotenv, find_dotenv
from sql_exchange import SqlExchange
from decimal import *

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def help(bot, update):
    help_msg = "\n".join([
        'Use /set <seconds> to set a timer',
        'Use /arbitrage <LTC/BTC> to check for arbitrage opportunities across markets',
        'Use /mktsummary <LTC/BTC> to check market summary on Bittrex',
        'Use /fetch_markets <LTC/BTC> to check all markets',
        'Use /sim <LTC/BTC> <days_ago> to run simulation of buysell bot on Bittrex from x days ago',
        'Use /pf <portfolio_name> to check all balances in your portfolio. A portfolio will be created for you if it doesnt exist',
        'Use /pf_limit_buy <portfolio_name> <ETH/BTC> <price> <quantity> to buy <quantity> of ETH at <price> using BTC for your portfolio.',
        'Use /pf_limit_sell <portfolio_name> <ETH/BTC> <price> <quantity> to sell <quantity> of ETH at <price> for BTC for your portfolio.',
        ])
    update.message.reply_text(help_msg)

def alarm(bot, job):
    """Send the alarm message."""
    bot.send_message(job.context, text='Beep!')

def fetch_markets(bot, update, args):
    """Fetch markets for symbol."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the market_symbol (eg. NXT/BTC)
        market_symbol = args[0]

        update.message.reply_text('Fetching markets for %s.' % (market_symbol))
        c = Crypto()
        result = c.fetch_markets(market_symbol)
        output = c.log_buffer + [str(result)]
        output = "\n".join(output)
        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /fetch_markets <ETH/BTC>')

def sim(bot, update, args):
    """Run simulation of buysell bot on Bittrex from x days ago."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the market_symbol (eg. NXT/BTC)
        market_symbol = args[0]
        days_ago = int(args[1])

        update.message.reply_text('Running simulation for %s looking back %s days ago' % (market_symbol, days_ago))
        log_buffer = Crypto.run_simulation(market_symbol, days_ago)
        output = "\n".join(log_buffer)
        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /mktsummary <ETH/BTC>')

def pf(bot, update, args):
    """Portfolio checking."""
    try:
        portfolio_name = args[0]

        sql_ex = SqlExchange(portfolio_name)
        totals = sql_ex.fetch_balance()

        output = ['Portfolio [%s] has:' % (portfolio_name)]
        for coin in totals:
            output.append('{0}: {1:.8g}'.format(coin, totals[coin]))

        output = "\n".join(output)
        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /pf <portfolio_name>')

def pf_limit_buy(bot, update, args):
    """Buy Currency."""
    try:
        portfolio_name, market_symbol, price, quantity = args

        sql_ex = SqlExchange(portfolio_name)
        currency, base_currency = market_symbol.split('/')
        order = sql_ex.limit_buy_order(currency, base_currency, Decimal(price), Decimal(quantity))
        if order:
            output = 'Bought %s %s at %s for portfolio [%s]' % (quantity, currency, price, portfolio_name)
        else:
            output = "Cannot buy\n"
            output += "\n".join(sql_ex.log_buffer)


        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /pf_limit_buy <portfolio_name> <ETH/BTC> <price> <quantity>')

def pf_limit_sell(bot, update, args):
    """Sell Currency."""
    try:
        portfolio_name, market_symbol, price, quantity = args

        sql_ex = SqlExchange(portfolio_name)
        currency, base_currency = market_symbol.split('/')
        order = sql_ex.limit_sell_order(currency, base_currency, Decimal(price), Decimal(quantity))
        if order:
            output = 'Sold %s %s at %s for portfolio [%s]' % (quantity, currency, price, portfolio_name)
        else:
            output = "Cannot sell\n"
            output += "\n".join(sql_ex.log_buffer)

        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /pf_limit_sell <portfolio_name> <ETH/BTC> <price> <quantity>')

def mktsummary(bot, update, args):
    """Checks for market summary potential."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the market_symbol (eg. NXT/BTC)
        market_symbol = args[0]

        update.message.reply_text('Checking for market summary for %s' % (market_symbol))
        c = Crypto()
        c.get_market_summary(market_symbol)
        output = "\n".join(c.log_buffer)
        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /mktsummary <ETH/BTC>')

def arbitrage(bot, update, args):
    """Checks for arbitrage potential."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the market_symbol (eg. NXT/BTC)
        market_symbol = args[0]

        update.message.reply_text('Checking for arbitrage potential on %s' % (market_symbol))
        c = Crypto()
        c.run_check_arbitrage(market_symbol)
        output = "\n".join(c.log_buffer)
        update.message.reply_text(output)

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /arbitrage <ETH/BTC>')

def set_timer(bot, update, args, job_queue, chat_data):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(args[0])
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return

        # Add job to queue
        job = job_queue.run_once(alarm, due, context=chat_id)
        chat_data['job'] = job

        update.message.reply_text('Timer successfully set!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


def unset(bot, update, chat_data):
    """Remove the job if the user changed their mind."""
    if 'job' not in chat_data:
        update.message.reply_text('You have no active timer')
        return

    job = chat_data['job']
    job.schedule_removal()
    del chat_data['job']

    update.message.reply_text('Timer successfully unset!')


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Run bot."""
    bot_key = os.environ.get("BOT_KEY")
    updater = Updater(bot_key)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", help))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("arbitrage", arbitrage,
                                    pass_args=True))
    dp.add_handler(CommandHandler("mktsummary", mktsummary,
                                    pass_args=True))
    dp.add_handler(CommandHandler("fetch_markets", fetch_markets,
                                    pass_args=True))
    dp.add_handler(CommandHandler("sim", sim,
                                    pass_args=True))                                
    dp.add_handler(CommandHandler("set", set_timer,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("pf", pf,
                                    pass_args=True)) 
    dp.add_handler(CommandHandler("pf_limit_buy", pf_limit_buy,
                                    pass_args=True))
    dp.add_handler(CommandHandler("pf_limit_sell", pf_limit_sell,
                                    pass_args=True))
    dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
