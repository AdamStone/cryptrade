""" Simple example of plotting and saving candle data while collecting live trades. """

from cryptrade import TradeStream, CandleStream

period = '15 min'

ts = TradeStream()
cs = CandleStream(ts, period)

cs.run()