from __future__ import division
from decimal import Decimal, getcontext
getcontext().prec=8

from PyQt4 import QtGui, QtCore

import conditions
from indicators import SMA, EMA

class Strategy(object):
    """ A Strategy is a set of Conditions which defines when 
    trades should be executed in backtesting or live trading. 
    
    AND and AND NOT relationships between Conditions are achieved using
    arithmetic operators, e.g. for conditions A and B,
        
        A + B yields a new Condition which represents A AND B
        A - B yields a new Condition which represents A AND NOT B
        
    OR relationships are achieved by passing a list of conditions to either
    set_buy_conditions() or set_sell_conditions; if any condition evaluates
    True on a check() call, the check returns True. 

    By default, a strategy will trade the full amount of a given currency. The
    set_risk(fraction_of_equity) method specifies a fraction of equity to risk 
    per trade instead, for risk-management strategies.
    
    Stoploss mechanisms are included as a special trade condition and can be 
    enabled by calling set_stoploss(fraction_of_entry_price). Unlike 
    Indicator/Condition-based market orders, stoploss sell orders are 
    placed as stop orders at the time of a buy order and are automatically 
    executed as soon as the threshold is met, without waiting for the candle 
    to finish. 
    
    The exchange fees can be specified by calling set_commission(fraction_of_trade).
    The Bitfinex .12% is used as the default case. This is used in predicting
    trade costs and risk management, but note that when livetrading, the fee 
    is determined by the exchange regardless of the value entered here. 
    """
    
    def __init__(self):
        self.buy_conditions = []
        self.sell_conditions = []
        self.trendChanges = []
        self.risk = Decimal(1)
        self.stoploss = Decimal(1)
        self.commission = Decimal(.0012)

    def set_buy_condition(self, buy_condition):
        self.buy_conditions = [buy_condition]

    def set_buy_conditions(self, buy_conditions):
        self.buy_conditions = []
        for condition in buy_conditions:
            self.buy_conditions.append(condition)
            
    def set_sell_condition(self, sell_condition):
        self.sell_conditions = [sell_condition]
    
    def set_sell_conditions(self, sell_conditions):
        self.sell_conditions = []
        for condition in sell_conditions:
            self.sell_conditions.append(condition)
    
    def set_risk(self, fraction_of_equity):
        self.risk = Decimal(str(fraction_of_equity))
        
    def set_stoploss(self, fraction_of_entry_price):
        self.stoploss = Decimal(str(fraction_of_entry_price))
        
    def set_commission(self, fraction_of_trade):
        self.commission = Decimal(str(fraction_of_trade))   

    def check(self, **kwargs): 
        for condition in self.buy_conditions:
            if condition.check(**kwargs):
                return 'Buy'
        for condition in self.sell_conditions:
            if condition.check(**kwargs):
                return 'Sell'

    

class MovingAverageCrossoverStrategy(Strategy):
    """ Trade based on a pair of moving averages, with a 'buy' condition
    obtained when the short-term average is higher than the long-term and 
    a 'sell' condition obtained in the reverse case. 
    """
    
    name = 'Moving average crossover'

    def __init__(self, ma1, ma2):
        super(MovingAverageCrossoverStrategy, self).__init__()
        self.averages = ma1, ma2 = sorted((ma1, ma2), key=lambda x: x.window) # deal with last vs last two; deal with stop orders

        trend_condition = conditions.GreaterThan(ma1, ma2)

        # buy if ma1 > ma2 and not positioned long
        buy_condition = trend_condition - conditions.LongPosition()
        
        # additionally, block buys if RecentStoploss condition is True
        buy_condition -= conditions.RecentStoploss(trend_condition)
        
        # sell if ma2 > ma1 and positioned long
        sell_condition = conditions.GreaterThan(ma2, ma1) + conditions.LongPosition()
        
        self.set_buy_condition( buy_condition )
        self.set_sell_condition( sell_condition )
        
    @staticmethod
    def qtFrame(parent=None):
        """ Handle for the GUI to access the associated setup frame.
        """
        return MovingAverageCrossoverFrame(parent)
        

class MovingAverageCrossoverFrame(QtGui.QFrame):
    """ GUI frame to be used in setting up the MovingAverageCrossover
    trading strategy. Since different strategies may generally require 
    different inputs, each subclass of Strategy to be used in the GUI should 
    include a qtFrame @staticmethod which points to a corresponding QFrame 
    object.
    """
    
    enableOk = QtCore.pyqtSignal()    
    disableOk = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super(MovingAverageCrossoverFrame, self).__init__(parent)

        layout = QtGui.QVBoxLayout()

        # indicators list
        self.avgModel = QtGui.QStandardItemModel()
        self.avgList = QtGui.QListView(self.parent())
        self.avgList.setModel(self.avgModel)
        self.avgModel.itemChanged.connect(self.checkValid)
        self.avgList.setMaximumHeight(100)
        
        # get current indicators from parent
        self.indicators = self.parent().parent().indicators
        for i, ind in enumerate(self.indicators):
            if type(ind[0]) in [SMA, EMA]:
                item = QtGui.QStandardItem(ind[0].label)
                item.setCheckable(True)
                item.setCheckState(QtCore.Qt.Unchecked)
                if i < 2 and len(self.indicators) >= 2:
                    item.setCheckState(QtCore.Qt.Checked)
                else:
                    item.setCheckState(QtCore.Qt.Unchecked)
                item.setSelectable(False)
                item.setEditable(False)
                item.indicatorObject = ind[0]
                self.avgModel.appendRow(item)
        
        layout.addWidget(QtGui.QLabel('Implemented averages (select 2)'))
        layout.addWidget(self.avgList)
        
        self.setLayout(layout)

    def checkValid(self):
        rows = self.avgModel.rowCount()
        checked = 0
        for i in range(rows):
            checked += self.avgModel.item(i).checkState()/2
        
        if checked == 2:
            self.enableOk.emit()
        else:
            self.disableOk.emit()

    def inputs(self):
        checked = []
        rows = self.avgModel.rowCount()
        for i in range(rows):
            item = self.avgModel.item(i)
            if item.checkState() == 2:
                checked.append(item.indicatorObject)
        return checked

    def reset(self):
        pass
    