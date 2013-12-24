""" Simplest example script to collect and store live trade data from Bitfinex API """

from cryptrade import TradeStream

ts = TradeStream()

ts.run()