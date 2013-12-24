""" Tools for handling trade data, candle data, and simulating trades. """

from __future__ import division
import os, csv, time
from datetime import datetime
import traceback
from decimal import Decimal, getcontext
getcontext().prec=8

from utilities import TRADES, CANDLES, ut_to_dt, dt_to_ut, build_data_directories, parse_period, pdelta, get_candle, trades_to_candles, save_candlefile
from analytics import Condition, Strategy, SMA, EMA, MACD
from plotting import Candleplot
from api import BitfinexAPI

            


class TradeStream(object):
    """ A TradeStream collects live data from exchange API 
    (currently only Bitfinex API supported). If record_trades is True, 
    trades will be recorded to a local file. 
    
    Note that multiple TradeStreams should not be run simultaneously for the 
    same market, or duplicate trades will be written to the file. """
    
    API_ACCESS = {'bitfinex':BitfinexAPI, 'bitstamp':BitfinexAPI}        
    
    def __init__(self, market='bitfinex_BTC_USD', record_trades=True, quiet=False):
        
        self.exchange, self.base, self.alt = market.split('_')

        # read trade data from file
        try:
            with open(TRADES+'{}_{}_{}'.format(self.exchange, self.base, self.alt), 'rb') as readfile:
                reader = csv.reader(readfile, delimiter=',')
                self.trades = [{'timestamp':int(row[0]), 'price':Decimal(row[1]), 'amount':Decimal(row[2])} for row in reader]
        except:
            self.trades = []        
        
        self.symbol = self.base.lower() + self.alt.lower()
        self.api = self.API_ACCESS[self.exchange]()
        self.record_trades = record_trades
        self.quiet = quiet        
        self.new_trades=[]
    
    def update(self):
        trades = sorted(self.api.trades({}, self.symbol), key=lambda x: int(x['timestamp']))
        new_trades = [{'timestamp':int(t['timestamp']), 'price':Decimal(t['price']), 'amount':Decimal(t['amount'])} 
                        for t in trades 
                        if t['timestamp'] > self.last_trade()['timestamp']
                        and t['exchange'] == self.exchange]
        
        if new_trades:
            self.new_trades = new_trades
            # print each new trade, and add it to the trade file if record_trades=True
            for trade in new_trades:
                if not self.quiet:
                    print "{}   {}   {} {}   {} {}".format(ut_to_dt(trade['timestamp']), self.exchange, trade['price'], self.alt, trade['amount'], self.base)
                
                self.trades.append({'timestamp':int(trade['timestamp']), 'price':Decimal(trade['price']), 'amount':Decimal(trade['amount'])})
                self.price = self.trades[-1]['price']
                
                # write new trades to tradefile
                if self.record_trades:
                    tradefile = TRADES+'{}_{}_{}'.format(self.exchange, self.base, self.alt)
                    if not os.path.exists(TRADES):
                        raw_input('Warning: Trade data directory not found. Create now?')
                        build_data_directories()                        
                        
                    with open(tradefile, 'a') as writefile:
                        writer = csv.writer(writefile, delimiter=',')
                        writer.writerow([trade['timestamp'], trade['price'], trade['amount']])

        else:
            self.new_trades = []

    def run(self, update_every=5):
        while True:
            time.sleep(update_every)    
            try:
                self.update()
            except:
                traceback.print_exc()   

    def last_trade(self):
        if self.trades:
            return self.trades[-1]
        else:
            return {'timestamp': 0 }          


class CandleStream(object):
    """ A CandleStream converts trade data from a TradeSource to candle data 
    for a given period. If plot_ncandles > 0, a candleplot will be created 
    and updated as new trade data are detected. Multiple candle streams can 
    be run from the same TradeSource. In that case, all the CandleStreams 
    should be updated before each new update of the TradeSource. 
    """
    
    def __init__(self, tradesource, period, indicators=[], plot_ncandles=50, record_candles=True, start=None):
        self.tradesource = tradesource
        self.p_value, self.p_unit = parse_period(period)
        self.period = period
        self.step = pdelta(self.p_value, self.p_unit)
        self.exchange, self.base, self.alt = tradesource.exchange, tradesource.base, tradesource.alt
        self.candlefile = CANDLES + '{}_{}_{}_{}{}'.format(self.exchange, self.base, self.alt, self.p_value, self.p_unit)   
        self.indicators = indicators
        self.record_candles = record_candles
        
        if plot_ncandles:
            self.plot_ncandles = plot_ncandles
            self.plot = Candleplot(interactive=True)
        else:            
            self.plot_ncandles=50
            self.plot = None

        # check for candle directory
        if not os.path.exists(CANDLES):
            print 'Checking for directory at ', CANDLES
            raw_input('Warning: Candle data directory not found. Create now?')
            build_data_directories()

        # check for candle file
        if os.path.exists(self.candlefile):
            with open(self.candlefile, 'rb') as readfile:
                reader = csv.reader(readfile, delimiter=',')
                if start:
                    self.closed_candles = [[int(candle[0])] + [Decimal(x) for x in candle[1:]] for candle in reader if ut_to_dt(candle[0]) < start]
                else:
                    self.closed_candles = [[int(candle[0])] + [Decimal(x) for x in candle[1:]] for candle in reader]
            self.active_candle = self.closed_candles.pop() 

        # if no candle file, check for trades in tradesource
        elif self.tradesource.trades:
            print 'No candlefile found; generating from tradesource...'
            if start:
                self.closed_candles = [[int(candle[0])] + [Decimal(x) for x in candle[1:]] 
                                        for candle in trades_to_candles(self.tradesource.trades, period)
                                        if ut_to_dt(candle[0]) < start]
            else:
                self.closed_candles = [[int(candle[0])] + [Decimal(x) for x in candle[1:]] 
                                        for candle in trades_to_candles(self.tradesource.trades, period)]
            self.active_candle = self.closed_candles.pop()
            
        # if no candles or trades
        else:
            print 'No candlefile found; no tradefile found; waiting for new trades...'
            self.closed_candles = []
            self.active_candle = []
            self.active_trades = []
            self.next_start = None
            

        if self.active_candle:
            self.next_start = ut_to_dt(self.active_candle[0]) + self.step       
        
            # assume last candle is not closed yet (check in update)
            self.last_closed_known = False
        
            # read trade data from most recent candle
            self.active_trades = [trade for trade in self.tradesource.trades 
                                    if trade['timestamp'] >= self.active_candle[0]]
                                
            current_candles = self.closed_candles[-(self.plot_ncandles-1):]+[self.active_candle]
            
        if self.closed_candles:
            # calculate indicators
    
            if self.indicators:
                for indicator in self.indicators:
                    indicator.calculate(self.closed_candles+[self.active_candle])
    
            # plotting
            if self.plot:
                self.plot.plot_candledata(current_candles, self.period, indicators=self.indicators)

    def update(self):
        """ Checks for new trades and updates the candle data, indicators, 
        and plot. 
        """
        
        new_trades = self.tradesource.new_trades
        if new_trades:
            
            self.active_trades += [{'timestamp':int(trade['timestamp']), 
                                        'price':Decimal(trade['price']), 
                                        'amount':Decimal(trade['amount'])} for trade in new_trades]
                                        
            if not self.next_start:
                first = ut_to_dt(self.active_trades[0]['timestamp'])
                start = datetime(year=first.year, month=first.month, day=first.day)
                while start + self.step < first:
                    start += self.step
                self.next_start = start + self.step
                self.active_candle = get_candle(dt_to_ut(start), self.active_trades)
                self.last_closed_known = False
            
            # dump older trades if active candle has closed, accounting for possible gaps
            while ut_to_dt(self.active_trades[-1]['timestamp']) > self.next_start:
                self.dump()
                
            # update active candle
            new_candle = get_candle(self.active_candle[0], new_trades)
            self.active_candle = self.update_candle(self.active_candle, new_candle)
            
            # update indicators
            if self.indicators:
                for indicator in self.indicators:
                    indicator.calculate(self.closed_candles+[self.active_candle])    
            
            # plotting
            if self.plot:
                self.plot.plot_candledata(self.closed_candles[-(self.plot_ncandles-1):] + [self.active_candle], self.period, indicators = self.indicators)

    def dump(self):
        """ Run once the candle is completed, to close the candle and record 
        it to the candle data file. 
        """
        to_dump = [t for t in self.active_trades if ut_to_dt(t['timestamp']) < self.next_start]
        to_keep = [t for t in self.active_trades if ut_to_dt(t['timestamp']) >= self.next_start]

        if len(to_dump):
            print '{} {}{} candle closed at {} with {} trades'.format(self.exchange, self.p_value, self.p_unit, to_dump[-1]['price'], len(to_dump))
            
            dump_candle = get_candle(self.active_candle[0], to_dump)
            
            self.closed_candles.append(dump_candle)       
        
            if self.record_candles:
                # if last entry not closed, pop out the last entry before rewriting with update
                if not self.last_closed_known:
                    save_candlefile(self.closed_candles, self.period, self.candlefile, replace=True)
                else:
                    save_candlefile([dump_candle], self.period, self.candlefile, replace=False)
        
        self.active_trades = to_keep
        self.active_candle = get_candle(dt_to_ut(self.next_start), [to_keep[0]])
        
        self.next_start += self.step

        # only closed candles are saved, so last will always be closed on further updates
        self.last_closed_known = True 


    def update_candle(self, active_candle, new_candle):
        """ Merges new trade data with an open candle. 
        """
        
        # starts, opens, closes, highs, lows, volumes
        if int(active_candle[0]) != int(new_candle[0]):
            print '(update_candle) Warning: Candle start times do not align!'
        elif len(active_candle) == 1:
            return new_candle
        else:
            start = active_candle[0]
            opening = active_candle[1]
            closing = new_candle[2]
            high = max([active_candle[3], new_candle[3]])
            low = min([active_candle[4], new_candle[4]])
            volume = sum([active_candle[5], new_candle[5]])
            return [start, opening, closing, high, low, volume]

    def run(self, update_every=10, update_src=True):
        while True:
            time.sleep(update_every)    
            try:
                if update_src:
                    self.tradesource.update()
                    
                self.update()
            except:
                traceback.print_exc()   
                
    def price(self):
        return self.tradesource.trades[-1]['price'] # should update to check order book



class Trader(object):
    """ Executes a (simulated) trading strategy on a CandleStream.
    """
    
    def __init__(self, candlesource, finances, position=None, update_every=10):
        
        self.candlesource = candlesource        

        self.exchange, self.base, self.alt = candlesource.exchange, candlesource.base, candlesource.alt
        self.symbol = self.base.lower() + self.alt.lower()
        
        self.indicators = self.candlesource.indicators
        self.finances = {cur: Decimal(owned) for cur, owned in finances.items()}
        
        self.strategy = Strategy(trader=self)
                     
        self.my_trades = []
        self.position = position
        self.update_every = update_every


    def price(self):
        return self.candlesource.price() # should update to check order book
            
            
    def exit_point(self):
        """ Calculates exit price points based on stoploss value specified by 
        Strategy.set_stoploss(). 
        """
        
        if self.my_trades:
            if self.position == 'long':
                return self.my_trades[-1][1] - (self.my_trades[-1][1] * self.strategy.stoploss)
            if self.position == None:
                return self.my_trades[-1][1] + (self.my_trades[-1][1] * self.strategy.stoploss)
    
    
    def equity(self):
        return self.finances[self.alt] + self.finances[self.base]*self.price()
    

    def update(self):
        self.candlesource.update()
        # check if trade should be executed
        action = self.strategy.check(self.position)
        if action:
            self.trade(action)        

                
    def trade(self, action):
        if action == 'buy':
            
            price = self.price()
            dollars_at_risk = self.strategy.risk * self.equity()
            price_move = price * self.strategy.stoploss       
            amount = dollars_at_risk / price_move       # buy based on risk management
            
            timestamp = datetime.utcnow()
            self.my_trades.append([dt_to_ut(timestamp), price, amount, 'buy'])
            self.position = 'long'
            self.finances[self.base] += amount
            self.finances[self.alt] -= price*amount
            
            print '{}   Buying {} {} at {}.'.format(timestamp, amount, self.base, self.price())
            
        if action == 'sell':
            
            price = self.price()
            amount = self.finances[self.base] # sell all to exit position
            
            timestamp = datetime.utcnow()
            self.my_trades.append([dt_to_ut(timestamp), price, amount, 'sell'])
            self.position = None
            self.finances[self.base] -= amount
            self.finances[self.alt] += price*amount            
            
            print '{}   Selling {} {} at {}.'.format(timestamp, amount, self.base, self.price())

        print 'Current finances: ', self.finances

    def run(self):
        while True:
            try:
                time.sleep(self.update_every)
                
                # check for new price moves
                self.candlesource.tradesource.update()
                
                # update candles
                self.candlesource.update()
                
                # update finances
                self.update()
            except:
                traceback.print_exc()


class CrossoverTrader(Trader):
    """ Simplified Trader implementation for live trading simulation for moving 
    average crossovers. TradeStream and CandleStream objects are created automatically.
    """
    
    def __init__(self, finances, period, avg_type, order1, order2, position=None, market='bitfinex_BTC_USD', record_candles=True, plot_ncandles=50, update_every=10):
        # create indicators
        
        fast, slow = sorted([order1, order2])        
        
        if avg_type in ['ema', 'EMA']:
            fast = EMA(fast)
            slow = EMA(slow) 
        
        elif avg_type in ['sma', 'SMA']:
            fast = SMA(fast)
            slow = SMA(slow)
    
        macd = MACD(fast, slow)
        
        indicators = [fast, slow, macd]
        
        # create trade data stream and record new trades to trade data file
        tradesource = TradeStream(market='bitfinex_BTC_USD', record_trades=True)
        
        # build candle stream on trade stream
        candlestream = CandleStream(tradesource, period, indicators, record_candles=record_candles, plot_ncandles=plot_ncandles)

        Trader.__init__(self, candlestream, finances)

        self.strategy.set_buy_conditions([ Condition(macd.greater_than, 0) ])
        self.strategy.set_sell_conditions([ Condition(macd.less_than, 0) ])
        
        self.update_every = update_every
        
    def update(self):

        # check trading strategy
        action = self.strategy.check(self.position)
        if action:
            self.trade(action)            
            
    def run(self):
        while True:
            try:
                time.sleep(self.update_every)
                
                # check for new price moves
                self.candlesource.tradesource.update()
                
                # update candles
                self.candlesource.update()
                
                # update finances
                self.update()
            except:
                traceback.print_exc()