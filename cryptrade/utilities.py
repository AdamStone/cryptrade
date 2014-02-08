""" General tools for file access, conversions, processing trade data. """

from __future__ import division
import os, sys, csv
import calendar
from datetime import datetime, timedelta
from decimal import Decimal, getcontext
getcontext().prec=8
import itertools
import traceback

import numpy as np


# when imported, ROOT is set to wherever the import was called
ROOT = os.path.dirname(os.path.realpath(sys.argv[0]))
DATA = os.path.join(ROOT, 'data/')

TRADES = os.path.join(DATA, 'trades/')
CANDLES = os.path.join(DATA, 'candles/')
BACKTESTS = os.path.join(DATA, 'backtests/')


def save_batchtest(filename, **kwds):
    if BACKTESTS not in filename:    
        filename = os.path.join(BACKTESTS, filename)
    
    np.savez(filename, **kwds)
        
    
def load_batchtest(filename):
    if BACKTESTS not in filename:    
        filename = os.path.join(BACKTESTS, filename)
        
        return np.load(filename)


def build_data_directories(path=None):
    """ Used to create data directories if not found. """
    path = os.path.join(ROOT, 'data/')        
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    os.chdir('data')
    
    if not os.path.exists(TRADES):
        os.makedirs(TRADES)
    if not os.path.exists(CANDLES):
        os.makedirs(CANDLES)    
    if not os.path.exists(BACKTESTS):
        os.makedirs(BACKTESTS)           
        

def ut_to_dt(ut):
    """ Convert unixtime to datetime. """
    return datetime.utcfromtimestamp(float(ut))


def dt_to_ut(dt): 
    """ Convert datetime to unixtime. """
    return calendar.timegm(dt.timetuple())
    
    
def parse_period(period):
    """ Accounts for various ways to define candle period, for 
    more flexible and intuitive input. """
    
    valid = ['d', 'day', 'days',
             'h', 'hr', 'hrs', 'hour', 'hours', 
             'm', 'min', 'mins', 'minute', 'minutes', 
             's', 'sec', 'secs', 'second', 'seconds']
    try:
        split = period.split(' ')
        if len(split) == 1:
            p_unit = 'h' # default
            grouped = itertools.groupby(period, lambda x: x in '1234567890.')
            for group in grouped:
                if group[0]: # value
                    p_value = ''.join(group[1])
                else: # unit
                    p_unit = ''.join(group[1])
        elif len(split) == 2:
            p_unit = split[1]
            p_value = split[0]
            
        if p_unit in valid:
            return int(p_value), p_unit[0]
        else:
            print p_unit
            raw_input( "Error: period should be given as a string in the form of 'intvalue timeunit'" )
            return None
            
    except:
        raw_input( "Error: period should be given as a string in the form of 'intvalue timeunit'" )


def pdelta(*args):
    """ Returns a timedelta object for a given period. Period can be passed in directly as a 
    single argument, e.g. pdelta('15 m'), or the p_value and p_unit can be passed separately, 
    e.g. pdelta(15, 'm'). """
    
    if len(args) == 2:
        p_value, p_unit = args
        
    elif len(args) == 1:
        p_value, p_unit = parse_period(*args)
    
    if p_unit == 'h':
        return timedelta(hours = p_value)
    if p_unit == 'm': 
        return timedelta(minutes = p_value)
    if p_unit == 's':
        return timedelta(seconds = p_value)    
        
    
def load_candlefile(candlefile):
    """ Get candles and period from a candle data file. """
    
    period = candlefile.split('_')[-1]
    try:
        candles = np.loadtxt(CANDLES + candlefile, delimiter=',')
    except:
        traceback.print_exc()
        candles = []
    return (candles, period)


def load_candlefiles(market, periods):
    """ Get candles from candle data files for given periods 
    from a given market. """

    try:
        len(periods)
    except:
        periods = [periods]
    
    candledict = {}
    for period in periods:
        p_value, p_unit = parse_period
        fname = market + '_' + str(p_value) + p_unit
        candles, period = load_candlefile(fname)
        candledict[period] = candles
        
    return candledict
    

def save_candlefile(candles, period, filename, replace=True):
    """ Save candle data to local file. If replace=True, an existing 
    file will be rewritten, else new candles will be appended. """
    
    p_value, p_unit = parse_period(period)

    if '_{}{}'.format(p_value, p_unit) not in filename:    
        filename += '_{}{}'.format(p_value, p_unit)
    
    if CANDLES not in filename:
        filename = os.path.join(CANDLES, filename)
        
    try:
        with open(filename, 'a') as writefile: pass
    except:
        print 'Checking for directory at ', CANDLES
        raw_input('Warning: Candle data directory not found. Create now?')
        build_data_directories()        
        
    if replace:
        with open(filename, 'wb') as writefile:
            writer = csv.writer(writefile)
            for row in candles:
                writer.writerow(row)
    else:
        with open(filename, 'a') as appendfile:
            writer = csv.writer(appendfile)
            for row in candles:            
                writer.writerow(row)


def get_candle(start, trades):
    """ Creates a candle from a given datetime and a given set of trades. 
    Note that the trade timestamps are not checked; currently, any trades 
    provided are presumed to occur within the candle. """

    opening = Decimal(trades[0]['price'])
    closing = Decimal(trades[-1]['price'])
    
#    print trades
    prices = [Decimal(trade['price']) for trade in trades]

    high, low = max(prices), min(prices) 
    
    
    volume = sum([Decimal(trade['amount']) for trade in trades])
    
    return [start, opening, closing, high, low, volume]


def tradefile_to_candles(tradefile, period):
    """ Reads trades from a trade file and converts to candles. """

    p_value, p_unit = parse_period(period) 
    
    tradefile = TRADES + tradefile
    
    reader = csv.reader(open(tradefile, 'rb'), delimiter=',')
    trades = [{'timestamp':row[0], 'price':row[1], 'amount': row[2]} for row in reader]
    
    return trades_to_candles(trades, period)
    
    
def trades_to_candles(trades, period):
    """ Returns a set of candles corresponding to a given list of trades. """

    p_value, p_unit = parse_period(period)

    first = ut_to_dt(trades[0]['timestamp'])
    start = datetime(year=first.year, month=first.month, day=first.day)
    step = pdelta(p_value, p_unit)
    
    while start < first:
        start += step
    
    bins = [ (dt_to_ut(start), []) ]
    for trade in trades:
        if int(trade['timestamp']) < int(dt_to_ut(start + step)):
            bins[-1][1].append(trade)
        else:
            start += step
            bins.append((dt_to_ut(start), [trade]))
    
    candles = []
    for start, trades in bins:
        candle = get_candle(start, trades)
        candles.append(candle)
    return candles