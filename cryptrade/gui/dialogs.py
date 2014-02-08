from PyQt4 import QtGui, QtCore
from decimal import Decimal, getcontext
getcontext().prec=8

from ..trading import ExchangeTrader
from ..analytics import SMA, EMA, MACD, MovingAverageCrossoverStrategy
from ..api import BitfinexAPI



class IndicatorDialog(QtGui.QDialog):
    """ Dialog for adding indicators to the MainWindow. 
    """
    def __init__(self, parent=None):
        super(IndicatorDialog, self).__init__(parent)  
        
        self.choices = [SMA, EMA, MACD]
        
        self.indicatorComboBox = QtGui.QComboBox(self)
        for choice in self.choices:
            self.indicatorComboBox.addItem(choice.name)
        self.indicatorComboBox.currentIndexChanged.connect(self.resetIndicatorFrame)
        
        self.add_button = QtGui.QPushButton('Add')
        self.add_button.setDefault(True)
        self.add_button.setEnabled(False)
        
        self.done_button = QtGui.QPushButton('Done')        
        self.done_button.setDefault(False)
        
        self.buttonBox = QtGui.QDialogButtonBox()        
        self.buttonBox.addButton(self.add_button, QtGui.QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.done_button, QtGui.QDialogButtonBox.AcceptRole)
        
        self.add_button.clicked.connect(self.clickedAdd)
        self.buttonBox.accepted.connect(self.clickedDone)
        
        self.grid = QtGui.QGridLayout()
        self.grid.addWidget(self.indicatorComboBox, 0, 0)
        
        self.indicatorFrame = self.getIndicatorFrame()
        self.indicatorFrame.enableAdd.connect(lambda: self.add_button.setEnabled(True))
        self.indicatorFrame.disableAdd.connect(lambda: self.add_button.setEnabled(False))
        
        self.grid.addWidget(self.indicatorFrame, 1, 0)
        self.grid.addWidget(self.buttonBox, 2, 0)

        self.setLayout(self.grid)
        self.setWindowTitle("Select indicator")
        self.indicatorFrame.checkValid()
        self.added = False
        
        self.grid.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        

    def clickedAdd(self):
        index = self.indicatorComboBox.currentIndex()
        selected = self.choices[index]
        args = self.indicatorFrame.inputs()
        indicator = selected(*args)
        self.parent().addIndicator(indicator)
        self.add_button.setDefault(True)
        self.add_button.setEnabled(False)
        self.done_button.setDefault(False)
        self.resetIndicatorFrame()
        self.added = True
        
    def clickedDone(self,):
        self.close()
        if self.added:
            self.parent().updatePlot()
        
    def resetIndicatorFrame(self):
        self.grid.removeWidget(self.indicatorFrame)
        self.indicatorFrame.setParent(None)
        
        self.indicatorFrame = self.getIndicatorFrame()
        self.grid.addWidget(self.indicatorFrame, 1, 0)
        self.add_button.setDefault(True)
        self.done_button.setDefault(False)
        self.indicatorFrame.enableAdd.connect(lambda: self.add_button.setEnabled(True)) 
        self.indicatorFrame.disableAdd.connect(lambda: self.add_button.setEnabled(False))
        self.indicatorFrame.checkValid()
        
    def getIndicatorFrame(self):
        current = self.choices[self.indicatorComboBox.currentIndex()]
        return current.qtFrame(self)




class TraderDialog(QtGui.QDialog):
    """ Dialog for setting up the TraderWindow. 
    """        
    def __init__(self, parent=None):
        super(TraderDialog, self).__init__(parent)
        self.setWindowTitle("Trader setup")
        
        self.choices = [MovingAverageCrossoverStrategy]
        
        # select strategy
        label1 = QtGui.QLabel('Trading strategy')
        self.strategyComboBox = QtGui.QComboBox()
        for choice in self.choices:
            self.strategyComboBox.addItem(choice.name)

        self.strategyFrame = self.getStrategyFrame()
        
        # candle period
        periodLabel = QtGui.QLabel('Candle period')
        self.periodCombo = QtGui.QComboBox(self)
        for p in self.parent().periodOptions:
            self.periodCombo.addItem(p+' candles')
        self.periodCombo.setToolTip('Candle period')
        self.periodCombo.setCurrentIndex(4)
        
        # parameters
        riskLabel = QtGui.QLabel('Equity to risk per trade')                
        self.riskInput = QtGui.QLineEdit('2.5%')
        self.riskInput.setToolTip(
'''As a fraction or percent of total equity, e.g. '0.025' or 
'2.5%'. This value determines the maximum potential loss per 
trade, and in conjunction with the stoploss value, the size
of each trade.''')
        
        stoplossLabel = QtGui.QLabel('Stoploss price move')
        self.stoplossInput = QtGui.QLineEdit('3%')
        self.stoplossInput.setToolTip(
'''As a fraction or percent of entry price, e.g. '0.03' or '3%'. 
A stop order will be placed after each trade to exit the position 
when this threshold is reached.''')

        commissionLabel = QtGui.QLabel('Commission loss per trade')
        self.commissionInput = QtGui.QLineEdit('0.12%')
        self.commissionInput.setToolTip(
'''Fraction or percent of each trade lost to exchange commission 
fees, e.g. '0.002' or '0.2%'.''')        
        
        # connect to validator
        for inp in (self.riskInput, self.stoplossInput, self.commissionInput):
            inp.textChanged.connect(self.tryEnableOk)
        
        # parameters grid layout
        self.parametersGrid = QtGui.QGridLayout()
        self.parametersGrid.addWidget(periodLabel, 0, 0)
        self.parametersGrid.addWidget(self.periodCombo, 0, 1)
        self.parametersGrid.addWidget(riskLabel, 1, 0)
        self.parametersGrid.addWidget(self.riskInput, 1, 1)
        self.parametersGrid.addWidget(stoplossLabel, 2, 0)
        self.parametersGrid.addWidget(self.stoplossInput, 2, 1)
        self.parametersGrid.addWidget(commissionLabel, 3, 0)
        self.parametersGrid.addWidget(self.commissionInput, 3, 1)
        
        # connect API frame
        self.apiFrame = QtGui.QFrame()
        self.apiFrame.setEnabled(False)
        self.apiCheckBox = QtGui.QCheckBox('Enable live trading')        
        self.apiCheckBox.stateChanged.connect(self.toggleFrame)
        self.apiCheckBox.setCheckState(QtCore.Qt.CheckState(False))
        
        keyLabel = QtGui.QLabel('API key:')
        self.keyInput = QtGui.QLineEdit()
        secretLabel = QtGui.QLabel('API secret:')
        self.secretInput = QtGui.QLineEdit()
            
        layout = QtGui.QVBoxLayout()
        layout.addWidget(keyLabel)
        layout.addWidget(self.keyInput)
        layout.addWidget(secretLabel)
        layout.addWidget(self.secretInput)
        self.apiFrame.setLayout(layout)                

        # button box
        self.buttonBox = QtGui.QDialogButtonBox()
        self.buttonBox.addButton(QtGui.QDialogButtonBox.Cancel)
        self.okButton = self.buttonBox.addButton(QtGui.QDialogButtonBox.Ok)
        self.okButton.setEnabled(False)
        
        # connect signals
        self.buttonBox.accepted.connect(self.clickedOk)
        self.buttonBox.rejected.connect(self.close)
        
        # main layout
        self.grid = QtGui.QGridLayout()
        self.grid.addWidget(label1, 0, 0)
        self.grid.addWidget(self.strategyComboBox, 1, 0)
        self.grid.addWidget(self.strategyFrame, 2, 0)
        self.grid.addLayout(self.parametersGrid, 3, 0)
        self.grid.addWidget(QtGui.QLabel(''))
        self.grid.addWidget(self.apiCheckBox, 5, 0)
        self.grid.addWidget(self.apiFrame, 6, 0)
        self.grid.addWidget(self.buttonBox, 7, 0)
        
        self.setLayout(self.grid)
        
    def toggleFrame(self):
        self.apiFrame.setEnabled(self.apiCheckBox.checkState())
        
    def getStrategyFrame(self):
        current = self.choices[self.strategyComboBox.currentIndex()]
        return current.qtFrame(self)
        
    def resetStrategyFrame(self):
        self.grid.removeWidget(self.strategyFrame)
        self.strategyFrame.setParent(None)
        self.strategyFrame = self.getStrategyFrame()
        self.grid.addWidget(self.strategyFrame, 2, 0)
        self.strategyFrame.enableOk.connect(self.tryEnableOk)
        self.strategyFrame.disableOk.connect(lambda: self.okButton.setEnabled(False))
        self.strategyFrame.checkValid()
        
    def show(self):
        self.resetStrategyFrame()
        self.keyInput.setText(self.parent().key)
        self.secretInput.setText(self.parent().secret)
        super(TraderDialog, self).show()
        
    def tryEnableOk(self):
        risk = self.riskInput.text()
        stoploss = self.stoplossInput.text()
        commission = self.commissionInput.text()
        
        for text in [risk, stoploss, commission]:        
            try:
                self.parsePercent(text)
            except:
                self.okButton.setEnabled(False)
                return 
                
        self.okButton.setEnabled(True)       

    def clickedOk(self):
        self.close()
        index = self.strategyComboBox.currentIndex()
        selected = self.choices[index]
        args = self.strategyFrame.inputs()
        strategy = selected(*args)
        
        period = self.parent().periodOptions[self.periodCombo.currentIndex()]
        risk = self.parsePercent(self.riskInput.text())
        stoploss = self.parsePercent(self.stoplossInput.text())
        commission = self.parsePercent(self.commissionInput.text())
        
        strategy.set_risk(risk)
        strategy.set_stoploss(stoploss)
        strategy.set_commission(commission)
        
        candleStream = self.parent().candleStreams[period]
        
        if self.apiCheckBox.checkState():
            api = BitfinexAPI()
            api.key = str(self.keyInput.text())
            api.secret = str(self.secretInput.text())
            trader = ExchangeTrader(candleStream, api, strategy)
        
        else:
            return
        
        self.parent().traderWindow.setTrader(trader)
        self.parent().traderWindow.show()
        
    def parsePercent(self, string):
        string = str(string)
        if '%' in string:
            ans = Decimal('0.01') * Decimal(string[:-1])
        else:
            ans = Decimal(string)
        return ans


class MessageAlertDialog(QtGui.QDialog):
    """ Alert dialog to display messages obtained from the API.
    """
    def __init__(self, message, parent=None):
        super(MessageAlertDialog, self).__init__(parent)
        
        # message
        label = QtGui.QLabel(str(message))
        
        # button box
        self.buttonBox = QtGui.QDialogButtonBox()
        self.okButton = self.buttonBox.addButton(QtGui.QDialogButtonBox.Ok)
        
        # connect signals
        self.buttonBox.accepted.connect(self.close)     
    
        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.buttonBox)
    
        self.setLayout(layout)
        self.setWindowTitle('Warning')
        self.setGeometry(300,300,200,150)
        self.exec_()