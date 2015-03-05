from PyQt4 import QtGui, QtCore

from ..utilities import ut_to_dt

from dialogs import MessageAlertDialog


class TraderWindow(QtGui.QWidget):
    """ If trading is activated, this window manages the Trader backend and
    displays finances and personal trade history. """

    def __init__(self, parent=None, mainWindow=None):
        super(TraderWindow, self).__init__(parent)

        # retain a non-parent connection to the MainWindow
        self.mainWindow = mainWindow

        # completed trades
        self.completedTradesBox = QtGui.QTextBrowser()
        self.completedTradesBox.setMinimumWidth(500)

        # open orders
        self.openOrdersBox = QtGui.QTextBrowser()
        self.openOrdersBox.setMaximumHeight(70)

        # current finances
        self.base = self.mainWindow.tradestream.base
        baseLabel = QtGui.QLabel(self.base.upper())
        self.baseValue = QtGui.QLineEdit('0')
        self.baseValue.setReadOnly(True)
        self.baseValue.setToolTip('Amount of {} currently held'
                                  .format(self.base.upper()))

        self.alt = self.mainWindow.tradestream.alt
        altLabel = QtGui.QLabel(self.alt.upper())
        self.altValue = QtGui.QLineEdit('0')
        self.altValue.setReadOnly(True)
        self.altValue.setToolTip('Amount of {} currently held'
                                 .format(self.alt.upper()))

        equityLabel = QtGui.QLabel('Equity')
        self.equityValue = QtGui.QLineEdit('0')
        self.equityValue.setReadOnly(True)
        self.equityValue.setToolTip(
            'Value of total assets in {}, based on last trade price'.format(
                self.alt.upper()))

        financeLayout = QtGui.QHBoxLayout()
        financeLayout.addWidget(baseLabel)
        financeLayout.addWidget(self.baseValue)
        financeLayout.addWidget(altLabel)
        financeLayout.addWidget(self.altValue)
        financeLayout.addWidget(equityLabel)
        financeLayout.addWidget(self.equityValue)

        # layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(QtGui.QLabel('Completed trades:'))
        layout.addWidget(self.completedTradesBox)
        layout.addWidget(QtGui.QLabel('Open orders:'))
        layout.addWidget(self.openOrdersBox)
        layout.addWidget(QtGui.QLabel('Current finances:'))
        layout.addLayout(financeLayout)

        self.setLayout(layout)
        self.setWindowTitle('Trader')
        self.setGeometry(500, 500, 600, 400)

        # timer for periodic requery
        self.requeryTimer = QtCore.QTimer(self)
        self.requeryTimer.timeout.connect(self.requery)

    def setTrader(self, trader):
        self.trader = trader
        self.requeryTimer.start(300000)  # requery every 5 minutes
        try:
            self.refresh()
        except:
            pass

    def setFinances(self):
        finances = self.trader.finances
        base = finances['exchange'][self.trader.base]['amount']
        self.baseValue.setText(str(base)[:8])
        alt = finances['exchange'][self.trader.alt]['amount']
        self.altValue.setText(str(alt)[:8])

        equity = self.trader.equity()
        self.equityValue.setText(str(equity)[:8])

    def setCompletedTrades(self):
        trades = self.trader.my_trades
        for trade in trades:
            """trade example:
            {u'timestamp': Decimal('1386924359.0'),
             u'price': Decimal('906.19'),
             u'type': u'Buy',
             u'amount': Decimal('0.6605'),
             u'exchange': u'bitstamp'}"""
            self.completedTradesBox.append("{}   {}   {} {}  at  {} {}".format(
                ut_to_dt(trade['timestamp']), trade['type'], trade['amount'],
                self.trader.base, trade['price'], self.trader.alt))
            self.completedTradesBox.moveCursor(QtGui.QTextCursor.End)

    def setOpenOrders(self):
        self.openOrdersBox.clear()
        for order in self.trader.openOrders:
            self.openOrdersBox.append("{}   {}   {}   {} {}  at  {} {}".format(
                ut_to_dt(order['timestamp']), order['type'], order['side'],
                order['original_amount'], self.trader.base, order['price'],
                self.trader.alt))
            self.openOrdersBox.moveCursor(QtGui.QTextCursor.End)

    def refresh(self):
        try:
            self.setFinances()
            self.setCompletedTrades()
            self.setOpenOrders()
        except:
            pass

    def requery(self):
        self.trader.queue.append(lambda: self.trader.getFinances())
        self.trader.queue.append(lambda: self.trader.getCompletedTrades())
        self.trader.queue.append(lambda: self.trader.getOpenOrders())

    def update(self):
        actionTaken = self.trader.update()
        self.refresh()
        if actionTaken:
            try:  # catch messages, if any
                for message in actionTaken['messages']:
                    MessageAlertDialog(message)
                self.trader.messages = []
            except:
                pass
