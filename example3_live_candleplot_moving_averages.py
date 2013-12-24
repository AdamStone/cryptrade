""" Extending the live_candleplot example to include technical indicators. """

from cryptrade import TradeStream, CandleStream
from cryptrade.analytics import EMA, MACD

period = '15 min'

# Indicators are passed in a list
indicators = [EMA(10), EMA(21)]

# MACD indicator takes two moving average objects as args
indicators.append(MACD(*indicators))

ts = TradeStream()
cs = CandleStream(ts, period, indicators)

cs.run()