from __future__ import division
import numpy as np
from decimal import Decimal, getcontext
getcontext().prec=8

from PyQt4 import QtGui, QtCore


class Indicator(object):
    """ Indicator is the base class for technical indicators like moving
    averages. Subclasses should include a calculate(candles) method which 
    defines the mathematics of the indicator, and a plot_type attribute
    which indicates whether it should be plotted on the large upper subplot 
    ('primary') or the smaller bottom subplot ('secondary') in the GUI. 
    
    Indicators can be used to define Conditions and can be directly compared 
    (e.g. EMA10 > EMA21) if containing value arrays of the same length. 
    Comparisons can also be made between Indicators and numbers, e.g. 
    MACD > 0.  Comparisons yield a boolean array of the same length. Care 
    should be taken when making comparisons this way or using the stored 
    values, since they represent only the result of the last calculate(candles) 
    call, which may become outdated.    
    """
    def __init__(self, label=None):
        """ label will be used in the GUI plot legend.
        """
        self.label = label
        self.values = None        
        

    def __lt__(self, other):
        try:
            return np.array(self.values) < np.array(other.values)
        except:
            return np.array(self.values) < other

    def __gt__(self, other):
        try:
            return np.array(self.values) > np.array(other.values)
        except:
            return np.array(self.values) > other

    def __le__(self, other):
        try:
            return np.array(self.values) <= np.array(other.values)
        except:
            return np.array(self.values) <= other

    def __ge__(self, other):
        try:
            return np.array(self.values) >= np.array(other.values)
        except:
            return np.array(self.values) >= other

    def __eq__(self, other):
        try:
            return np.array(self.values) == np.array(other.values)
        except:
            return np.array(self.values) == other

    def __ne__(self, other):
        try:
            return np.array(self.values) != np.array(other.values)
        except:
            return np.array(self.values) != other
        
    def __getitem__(self, arg):
        return np.array(self.values)[arg]




class SMA(Indicator):
    """ Simple moving average. """
    
    name='Simple moving average'
    
    def __init__(self, window):
        super(SMA, self).__init__(label='SMA ' + str(window))
        self.window = int(window)
        self.plot_type = 'primary'
        
    def calculate(self, candles):
        closes = np.array(candles).transpose()[2]
        values = []
        for i, price in enumerate(closes):
            if i < self.window:
                pt = sum(closes[:i+1])/(i+1)
            else:
                pt = sum(closes[i-self.window+1:i+1])/self.window
            values.append(pt)
        self.values = np.array(values)
        return self.values
        
    @staticmethod
    def qtFrame(parent):
        """ Handle for the GUI to access the associated setup frame.
        """
        return SMAFrame(parent)
        
        
class SMAFrame(QtGui.QFrame):
    """ GUI frame for setting up an SMA. 
    """
    enableAdd = QtCore.pyqtSignal()    
    disableAdd = QtCore.pyqtSignal()
    
    def __init__(self, parent):
        super(SMAFrame, self).__init__(parent)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        label = QtGui.QLabel('Window:')
        self.window = QtGui.QLineEdit(self)
        self.window.textChanged.connect(self.checkValid)
        self.window.setFocus()
        hbox.addWidget(label)
        hbox.addWidget(self.window)
        self.setLayout(hbox)

    def checkValid(self):
        """ Check if input fields are valid to enable OK button. 
        """
        try:
            int(self.window.text())
            for ind in self.parent().parent().indicators:
                if type(ind[0]) == SMA and ind[0].window == int(self.window.text()):
                    self.disableAdd.emit()
                    return
            self.enableAdd.emit()
        except:
            self.disableAdd.emit()
            
    def inputs(self):
        """ Get the appropriate values from the frame to pass to the
        constructor of the indicator. 
        """
        return (self.window.text(),)
        
    def reset(self):
        pass


class EMA(Indicator):
    """ Exponential moving average. 
    """
    name = 'Exponential moving average'
    
    def __init__(self, window):
        Indicator.__init__(self, label = 'EMA ' + str(window))
        self.window = int(window)
        self.plot_type = 'primary'

    def calculate(self, candles):
        closes = np.array(candles).transpose()[2]
        closes = [Decimal(x) for x in closes]
        values = []
        m = Decimal(2 / (self.window + 1))
        for i, price in enumerate(closes):
            if i < self.window:
                pt = sum(closes[:i+1])/(i+1)
            else:
                pt = (closes[i] - values[-1]) * m + values[-1]
            values.append(pt)
        self.values = np.array(values)
        return self.values
        
    @staticmethod
    def qtFrame(parent=None):
        """ Handle for the GUI to access the associated setup frame.
        """        
        return EMAFrame(parent)
        

class EMAFrame(QtGui.QFrame):
    """ GUI frame for setting up an EMA. 
    """
    enableAdd = QtCore.pyqtSignal()    
    disableAdd = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super(EMAFrame, self).__init__(parent)       
        
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch(1)
        label = QtGui.QLabel('Window:')
        self.window = QtGui.QLineEdit(self)
        self.window.setFocus()
        self.window.textChanged.connect(self.checkValid)
        hbox.addWidget(label)
        hbox.addWidget(self.window)
        self.setLayout(hbox)

    def checkValid(self):
        """ Check if input fields are valid to enable OK button. 
        """
        try:
            int(self.window.text())
            for ind in self.parent().parent().indicators:
                if type(ind[0]) == EMA and ind[0].window == int(self.window.text()):
                    self.disableAdd.emit()
                    return
            self.enableAdd.emit()
        except:
            self.disableAdd.emit()

    def inputs(self):
        """ Get the appropriate values from the frame to pass to the
        constructor of the indicator. 
        """
        return (self.window.text(),)

    def reset(self):
        pass
        

class MACD(Indicator):
    """ Moving average convergence-divergence. """
    
    name = 'Moving average convergence divergence'
    
    def __init__(self, ma1, ma2):
        Indicator.__init__(self, label = 'MACD')
        self.averages = sorted((ma1, ma2), key=lambda x: x.window)
        self.plot_type = 'secondary'

    def calculate(self, candles):
        self.values = self.averages[0].calculate(candles) - self.averages[1].calculate(candles)
        return self.values
    
    @staticmethod
    def qtFrame(parent=None):
        """ Handle for the GUI to access the associated setup frame.
        """        
        return MACDFrame(parent)
        


class MACDFrame(QtGui.QFrame):
    """ GUI frame for setting up a MACD. 
    """    
    enableAdd = QtCore.pyqtSignal()    
    disableAdd = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super(MACDFrame, self).__init__(parent)

        layout = QtGui.QVBoxLayout()

        self.avgModel = QtGui.QStandardItemModel()
        self.avgList = QtGui.QListView(self.parent())
        self.avgList.setModel(self.avgModel)
        self.avgModel.itemChanged.connect(self.checkValid)
        self.avgList.setMaximumHeight(100)
        
        # get existing indicators from parent
        self.indicators = self.parent().parent().indicators
        for i, ind in enumerate(self.indicators):
            if type(ind[0]) in [SMA, EMA]:
                item = QtGui.QStandardItem(ind[0].label)
                item.setCheckable(True)
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
        """ Check if input fields are valid to enable OK button. 
        """
        # see what's currently checked
        current = []
        rows = self.avgModel.rowCount()
        for i in range(rows):
            item = self.avgModel.item(i)
            checked = item.checkState()
            if checked:
                avg = item.indicatorObject
                current.append((type(avg), avg.window))
        current = sorted(current, key=lambda x: x[1])
        
        # if more or less than 2, disableAdd
        if len(current) != 2:
            self.disableAdd.emit()
            
        else:
            # check if the same MACD is already implemented
            for ind in self.parent().parent().indicators:
                if type(ind[0]) == MACD:
                    averages = [(type(avg), avg.window) for avg in ind[0].averages]
                    if averages == current:
                        self.disableAdd.emit()
                        return
            
            # if not, enableAdd
            self.enableAdd.emit()

    def inputs(self):
        """ Get the appropriate values from the frame to pass to the
        constructor of the indicator. 
        """
        checked = []
        rows = self.avgModel.rowCount()
        for i in range(rows):
            item = self.avgModel.item(i)
            if item.checkState() == 2:
                checked.append(item.indicatorObject)
        return checked
        
    def reset(self):
        pass