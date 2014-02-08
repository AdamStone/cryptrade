import sys
from PyQt4 import QtGui, QtCore

from ..utilities import ut_to_dt
from ..trading import TradeStream, CandleStream
from ..plotting import CandlePlot

from traderWindow import TraderWindow
from dialogs import IndicatorDialog, TraderDialog

class MouseEventFilter(QtCore.QObject):
    """ Event filter used to stop update timer while mouse button is held down.
    Intended to prevent non-responsiveness due to an update occuring during 
    combobox selection by click-select-release method. 
    """
    def __init__(self, parent):
        super(MouseEventFilter, self).__init__()
        self.parent = parent
    
    def eventFilter(self, receiver, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            self.parent.timer.stop()
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            self.parent.timer.start()
            
        # continue normal event processing
        return super(MouseEventFilter, self).eventFilter(receiver, event)


class MainWindow(QtGui.QMainWindow):
    """ Main screen of GUI for visualizing market data. """
    def __init__(self, record_trades=True, record_candles=True):
        
        self.app = QtGui.QApplication(sys.argv)
        self.mouseEventFilter = MouseEventFilter(parent=self)
        self.app.installEventFilter(self.mouseEventFilter)        
        
        super(MainWindow, self).__init__()
        
        self.key = ''
        self.secret = ''        
        
        self.tradestream = TradeStream(record_trades=record_trades, quiet=True)
        self.indicators = []
        
        self.marketOptions = ['bitfinex_BTC_USD']#,'bitstamp_BTC_USD']
        self.periodOptions = ['5 minute', '10 minute', '15 minute', '30 minute', 
                              '1 hour', '2 hour', '6 hour', '12 hour', '24 hour']
                              
        self.candleStreams = {}
        for period in self.periodOptions:
            self.candleStreams[period] = CandleStream(self.tradestream, 
                                    period, record_candles=record_candles, quiet=True)        
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        
        # initialize windows and dialogs
        self.indicatorDialog = IndicatorDialog(self)
        self.traderDialog = TraderDialog(self)
        self.traderWindow = TraderWindow(mainWindow=self)
        
        self.createMainFrame()
        
        
    def createMainFrame(self):
        
        self.mainFrame = QtGui.QWidget()
        
        # mpl figure
        self.figure = CandlePlot(parent=self.mainFrame)
        self.plotDelayTimer = QtCore.QTimer(self)
        self.plotDelayTimer.setSingleShot(True)
        self.plotDelayTimer.timeout.connect(self.updatePlot)             
        
        # tradestream textbox
        self.textBox = QtGui.QTextBrowser()
        self.textBox.setMinimumWidth(500)
        self.textBox.setToolTip('Recent trades')
        for trade in self.tradestream.trades[-50:]:
            self.textBox.append("{}   {}   {} {}   {} {}".format(ut_to_dt(
                trade['timestamp']), self.tradestream.exchange, trade['price'], 
                self.tradestream.alt, trade['amount'], self.tradestream.base))  
        self.textBox.moveCursor(QtGui.QTextCursor.End)
    
        # market selection        
        self.marketCombo = QtGui.QComboBox(parent=self.mainFrame)
        for market in self.marketOptions:
            self.marketCombo.addItem(market)
        self.marketCombo.setToolTip('Market')
        
        # candle period
        self.period = QtGui.QComboBox(self.mainFrame)
        for p in self.periodOptions:        
            self.period.addItem(p+' candles')
        self.period.setToolTip('Candle period')
        self.period.setCurrentIndex(2)
        self.period.currentIndexChanged[str].connect(lambda: self.delayedPlot(2000))

        # 'Add indicators' button
        self.indicatorsButton = QtGui.QPushButton('Add indicators')
        self.indicatorsButton.clicked.connect(self.indicatorDialog.show)

        # 'Trader setup' button
        self.traderButton = QtGui.QPushButton('Trader setup')
        self.traderButton.clicked.connect(self.traderDialog.show)

        # options layout
        options = QtGui.QVBoxLayout()        
        options.addWidget(self.marketCombo)     
        options.addWidget(self.period)
        options.addWidget(self.indicatorsButton)
        options.addWidget(self.traderButton)
        
        # indicators list
        self.indicatorModel = QtGui.QStandardItemModel()
        self.indicatorList = QtGui.QListView(self.mainFrame)
        self.indicatorList.setModel(self.indicatorModel)
        self.indicatorModel.itemChanged.connect(lambda: self.delayedPlot(100))
        self.indicatorList.setToolTip('Implemented indicators')
        
        # bottom panel layout
        bottomPanel = QtGui.QHBoxLayout()
        bottomPanel.addWidget(self.textBox)
        bottomPanel.addLayout(options)
        bottomPanel.addWidget(self.indicatorList)
        
        # main frame layout
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.figure.canvas)
        vbox.addLayout(bottomPanel)
        self.mainFrame.setLayout(vbox)
        self.setCentralWidget(self.mainFrame)
        
        # initialize
        self.setWindowTitle('Market view')
        self.timer.start(20000)
        self.show()
        self.updatePlot()
        
            
    def addIndicator(self, indicator):
        item = QtGui.QStandardItem(indicator.label)
        item.setCheckable(True)
        item.setCheckState(QtCore.Qt.Checked)
        item.setSelectable(False)
        item.setEditable(False)
        self.indicators.append((indicator, item))
        self.indicatorModel.appendRow(item)
        
        
    def currentPeriod(self):
        index = self.period.currentIndex()
        return self.periodOptions[index]
        
        
    def updateTextBox(self, new_trades):
            for trade in self.tradestream.new_trades:
                self.textBox.append("{}   {}   {} {}   {} {}".format(ut_to_dt(
                    trade['timestamp']), self.tradestream.exchange, trade['price'], 
                    self.tradestream.alt, trade['amount'], self.tradestream.base))   
            self.textBox.moveCursor(QtGui.QTextCursor.End)
            
            return True


    def delayedPlot(self, delay):
        """ Used to slightly delay plot update upon changing of e.g. combobox
        selection, so that quickly scrolling through the values doesn't attempt
        to update the plot at each step. 
        """
        self.plotDelayTimer.start(delay)


    def updatePlot(self):
        self.plotDelayTimer.stop()
        period = self.currentPeriod()
        candleStream = self.candleStreams[period]
        candles = candleStream.get_candles(ncandles=200)
        plotIndicators = [indc[0] for indc in self.indicators if indc[1].checkState()] # checked indicators here are calculated within plot()
        try:
            self.figure.plot(candles, period, indicators=plotIndicators, ncandles=int(len(candles)/2))
        except:
            # candle data probably empty; ignore and wait for trades
            pass


    def update(self):
        if self.tradestream.update(): # if new trades obtained
            self.updateTextBox(self.tradestream.new_trades)

            # update candles
            for candleStream in self.candleStreams.values():
                candleStream.update()            
            
            # update plot
            self.updatePlot()
            
        # update traderWindow regardless of new trades, to attempt to process queue
        if self.traderWindow.isVisible():
            self.traderWindow.update()
    
    
    def setApiKey(self, key, secret):
        self.key = key
        self.secret = secret
    
        
    def run(self):
        sys.exit(self.app.exec_())