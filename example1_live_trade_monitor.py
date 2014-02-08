#!/usr/bin/python

""" Collect and store live trade data from Bitfinex API """

from cryptrade import TradeStream

# if record_trades, a data directory and trade data file will be created
TradeStream(record_trades=True).run()