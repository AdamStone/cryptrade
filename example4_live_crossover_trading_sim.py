""" Simple live trading simulation of a moving average crossover strategy. """

from cryptrade import CrossoverTrader

# choose candle period
period = '15 m'

# set initial finances as a dict
finances =  {'USD': 1000., 'BTC': 0.}

# CrossoverTrader is included as a more convenient way to set up a crossover trading strategy; 
# it creates TradeStream and CandleStream objects and sets trading Conditions internally
trader = CrossoverTrader(finances, period, 'EMA', 10, 21)

# refine trading strategy
strategy = trader.strategy
strategy.set_risk(0.025)          # fraction of equity to risk per trade
strategy.set_stoploss(0.05)       # fraction of entry price to exit position
strategy.set_commission(0.002)    # fraction of trade lost to commission/slippage

# run
trader.run()