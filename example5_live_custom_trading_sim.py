""" Live trading simulation of a custom moving average crossover strategy with threshold. """

from cryptrade import Trader, TradeStream, CandleStream, Condition
from cryptrade.analytics import SMA, MACD

# choose candle period
period = '15 m'

# set initial finances as a dict
finances =  {'USD': 1000., 'BTC': 0.}

fast = SMA(10)
slow = SMA(21)
macd = MACD(slow, fast)

indicators = [fast, slow, macd]

ts = TradeStream()
cs = CandleStream(ts, period, indicators)

# Trader is more general than CrossoverTrader. A candlestream must be provided, 
# and buy and sell Conditions must be specified. 
trader = Trader(cs, finances)

# Rather than trading as soon as MACD changes sign, wait until threshold is reached.
threshold = 0.5

# set trading Conditions
strategy = trader.strategy
strategy.set_buy_conditions([ Condition(macd.greater_than, threshold) ])
strategy.set_sell_conditions([ Condition(macd.less_than, -threshold) ])

# refine trading strategy
strategy.set_risk(0.025)          # fraction of equity to risk per trade
strategy.set_stoploss(0.05)       # fraction of entry price to exit position
strategy.set_commission(0.002)    # fraction of trade lost to commission/slippage

# run
trader.run()