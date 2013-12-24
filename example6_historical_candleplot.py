""" Example of a static plot of data from candle file, along with indicators. """

from cryptrade.analytics import EMA, MACD
from cryptrade.plotting import Candleplot

from datetime import datetime, timedelta

# candlefiles are saved with filenames in the form of 
# exchange_BASE_ALT_period where period is given by 
# a number and the first letter of the time unit 
# (m for minutes, h for hours) with no space, e.g. '15m' or '1h'
candlefile = 'bitfinex_BTC_USD_15m'

# Indicators are passed in a list
indicators = [EMA(10), EMA(21)]

# MACD indicator takes two moving average objects as args
indicators.append(MACD(*indicators))

# Time frame is specified with datetime objects
#end = datetime(year=2012, month=11, day=9)
end = datetime.utcnow()
start = end - timedelta(minutes=50*15) # 50 15-minute candles

# create and show plot
cp = Candleplot()
cp.plot_candlefile(candlefile, start, end, indicators)