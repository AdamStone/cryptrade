""" Tools related to technical analysis, e.g. analytic indicators for use in 
mechanical trading strategies. """

from __future__ import division
import numpy as np
from decimal import Decimal, getcontext
getcontext().prec=8


class Condition(object):
    """ Generic class for defining conditions at which trades should be executed. 
    Basically, it stores a function to be evaluated later (when check() is called). 
    Conditions can be added in order to create AND relationships. Conditions 
    would generally involve Indicators, e.g. function = MACD.greater_than(0).
    """
    def __init__(self, function, *args):
        # function to be checked
        self.function = function

        # args to that function
        self.args = args

    def check(self):
        return self.function(*self.args)

    # 
    def __add__(self, other):
        f1, a1 = self.function, self.args
        f2, a2 = other.function, other.args
        def merged(f1, a1, f2, a2): 
            return f1(*a1) and f2(*a2)
        return Condition(merged, f1, a1, f2, a2)
        
    def __radd__(self, other):
        f1, a1 = self.function, self.args
        f2, a2 = other.functon, other.args
        def merged(f1, a1, f2, a2): 
            return f1(*a1) and f2(*a2)
        return Condition(merged, f1, a1, f2, a2)



class Strategy(object):
    """ A Strategy is a set of Conditions which defines when 
    trades should be executed in backtesting or live trading. For AND 
    relationships between conditions, they should be added together.
    For OR relationships, they should be passed as separate list elements. 

    By default, a strategy will trade the full amount of a given currency. The
    set_risk(fraction_of_equity) method specifies a fraction of equity to risk 
    per trade instead.
    
    Stoploss conditions are included as a special case and can be implemented
    simply by calling set_stoploss(fraction_of_entry_price). Unlike Indicators, 
    stoploss trades are executed as soon as the threshold is met, without 
    waiting for the candle to finish. 
    
    The exchange fees can be specified by calling set_commission(fraction_of_trade).
    The Bitfinex .12% is used as the default case.
    
    The check() method is regularly called by the Trader. This first checks
    if buy or sell conditions have been met, then checks for stoploss trades. 
    """
    
    def __init__(self, trader=None):
        self.trader = trader
        self.buy_conditions = []
        self.sell_conditions = []
        self.risk = Decimal(1)
        self.stoploss = None
        self.commission = Decimal(.0012)

    def set_buy_conditions(self, conditions):
        for condition in conditions:
#            condition.action = 'buy'
            self.buy_conditions.append(condition)
    
    def set_sell_conditions(self, conditions):
        for condition in conditions:
#            condition.action = 'sell'
            self.sell_conditions.append(condition)
    
    def set_risk(self, fraction_of_equity):
        self.risk = Decimal(fraction_of_equity)
        
    def set_stoploss(self, fraction_of_entry_price):
        self.stoploss = Decimal(fraction_of_entry_price)
        
    def set_commission(self, fraction_of_trade):
        self.commission = Decimal(fraction_of_trade)
    
    def check(self, position):
        for condition in self.buy_conditions:
            if condition.check() and position != 'long':
                return 'buy'
        for condition in self.sell_conditions:
            if condition.check() and position == 'long':
                return 'sell'
                
        # check stoplosses
        if self.trader.exit_point():
            if position == 'long':        
                if self.trader.price() < self.trader.exit_point():
                    print 'stoploss sell triggered.'
                    print self.trader.price(), self.trader.exit_point()
                    return 'sell'
            if position == None:
                if self.trader.price() > self.trader.exit_point():
                    print 'stoploss buy triggered.'
                    print self.trader.price(), self.trader.exit_point()            
                    return 'buy'
        

 

class Indicator(object):
    """ Indicator is the base class for technical indicators like moving
    averages. Subclasses should include a calculate(candles) method which 
    defines the mathematics of the indicator, and a plot_type attribute
    which indicates whether it should be plotted on the large upper subplot (
    'primary') or the smaller bottom subplot ('secondary'). 
    
    Indicators are used to define Conditions and can be directly compared 
    (e.g. EMA10 > EMA21). Comparisons consider both the most recent candle 
    (assumed in-progress) and the second-most-recent candle, such that Conditions
    based on Indicator comparisons are not triggered until a full candle is 
    closed. Comparisons can also be made between Indicators and numbers, e.g.
    MACD > 0. 
    
    In order to pass such comparisons to Condition objects to be evaluated 
    during Strategy.check() calls, wrapper functions with more intuitive 
    names than the built-ins are provided. 
    
    """
    
    def __init__(self, name):
        self.name = name
        
    def less_than(self, other):
        return self < other

    def less_than_equals(self, other):
        return self <= other
        
    def greater_than(self, other):
        return self > other

    def greater_than_equals(self, other):
        return self >= other
        
    def equals(self, other):
        return self == other

    def not_equal(self, other):
        return self != other
        
    # defining the built-in comparisons to consider the last closed candle
    def __lt__(self, other):
        try:
            ov2, ov1 = other.values[-2:]
        except:
            ov2 = ov1 = other            
        if self.values[-1] < ov1 and self.values[-2] < ov2:
            return True
        else:
            return False

    def __gt__(self, other):
        try:
            ov2, ov1 = other.values[-2:]
        except:
            ov2 = ov1 = other            
        if self.values[-1] > ov1 and self.values[-2] > ov2:
            return True
        else:
            return False

    def __le__(self, other):
        try:
            ov2, ov1 = other.values[-2:]
        except:
            ov2 = ov1 = other            
        if self.values[-1] <= ov1 and self.values[-2] <= ov2:
            return True
        else:
            return False

    def __ge__(self, other):
        try:
            ov2, ov1 = other.values[-2:]
        except:
            ov2 = ov1 = other            
        if self.values[-1] >= ov1 and self.values[-2] >= ov2:
            return True
        else:
            return False

    def __eq__(self, other):
        try:
            ov2, ov1 = other.values[-2:]
        except:
            ov2 = ov1 = other            
        if self.values[-1] == ov1 and self.values[-2] == ov2:
            return True
        else:
            return False

    def __ne__(self, other):
        try:
            ov2, ov1 = other.values[-2:]
        except:
            ov2 = ov1 = other            
        if self.values[-1] == ov1 and self.values[-2] == ov2:
            return False
        else:
            return True



class SMA(Indicator):
    """ Simple moving average. """
    def __init__(self, order):
        Indicator.__init__(self, name = 'SMA ' + str(order))
        self.order = order
        self.plot_type = 'primary'
        
    def calculate(self, candles):
        closes = np.array(candles).transpose()[2]
        values = []
        for i, price in enumerate(closes):
            if i < self.order:
                pt = sum(closes[:i+1])/(i+1)
            else:
                pt = sum(closes[i-self.order+1:i+1])/self.order
            values.append(pt)
        self.values = np.array(values)
        return self.values



class EMA(Indicator):
    """ Exponential moving average. """
    def __init__(self, order):
        Indicator.__init__(self, name = 'EMA ' + str(order))
        self.order = order
        self.plot_type = 'primary'

    def calculate(self, candles):
        closes = np.array(candles).transpose()[2]
        closes = [Decimal(x) for x in closes]
        values = []
        m = Decimal(2 / (self.order + 1))
        for i, price in enumerate(closes):
            if i < self.order:
                pt = sum(closes[:i+1])/(i+1)
            else:
                pt = (closes[i] - values[-1]) * m + values[-1]
            values.append(pt)
        self.values = np.array(values)
        return self.values



class MACD(Indicator):
    """ Moving average convergence-divergence. """
    def __init__(self, ma1, ma2):
        Indicator.__init__(self, name = 'MACD')
        self.averages = sorted((ma1, ma2), key=lambda x: x.order)
        self.plot_type = 'secondary'

    def calculate(self, candles):
        self.values = self.averages[0].calculate(candles) - self.averages[1].calculate(candles)
        return self.values