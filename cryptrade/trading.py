""" Tools for handling trade data, candle data, and simulating trades. """

from __future__ import division
import os
import csv
import time
from datetime import datetime, timedelta
import itertools
import traceback
from decimal import Decimal, getcontext
getcontext().prec = 8

from utilities import (TRADES, CANDLES, ut_to_dt, dt_to_ut,
                       build_data_directories, parse_period, pdelta,
                       get_candle, trades_to_candles, save_candlefile)
from api import BitfinexAPI


class TradeStream(object):
    """
    A TradeStream collects live data from exchange API
    (currently only Bitfinex API supported). If record_trades is True,
    trades will be recorded to a local file.

    Note that multiple TradeStreams should not be run simultaneously for the
    same market, or duplicate trades will be written to the file.
    """
    API_ACCESS = {'bitfinex': BitfinexAPI, 'bitstamp': BitfinexAPI}

    def __init__(self, market='bitfinex_BTC_USD',
                 record_trades=True, quiet=False):

        self.exchange, self.base, self.alt = (item.lower()
                                              for item in market.split('_'))
        self.symbol = self.base + self.alt
        self.api = self.API_ACCESS[self.exchange]()
        self.record_trades = record_trades
        self.quiet = quiet

        try:
            with open(TRADES+'{}_{}_{}'.format(self.exchange,
                      self.base, self.alt), 'rb') as readfile:
                reader = csv.reader(readfile, delimiter=',')
                self.trades = [
                    {'timestamp': int(row[0]),
                     'price': Decimal(row[1]),
                     'amount': Decimal(row[2])}
                    for row in reader]
        except:
            self.trades = []
            self.update()

    def update(self):
        self.new_trades = []
        response = self.api.trades({}, self.symbol)
        if response:
            trades = sorted(response, key=lambda x: int(x['timestamp']))

            new_trades = [{'timestamp': int(t['timestamp']),
                           'price': Decimal(t['price']),
                           'amount': Decimal(t['amount'])}
                          for t in trades
                          if t['timestamp'] > self.last_trade()['timestamp']
                          and t['exchange'] == self.exchange]

            if new_trades:
                self.new_trades = new_trades
                # print each new trade, and add it to the
                # trade file if record_trades==True
                for trade in new_trades:
                    if not self.quiet:
                        print "{}   {}   {} {}   {} {}".format(
                            ut_to_dt(trade['timestamp']), self.exchange,
                            trade['price'], self.alt, trade['amount'],
                            self.base)

                    self.trades.append({'timestamp': int(trade['timestamp']),
                                        'price': Decimal(trade['price']),
                                        'amount': Decimal(trade['amount'])})
                    self.price = self.trades[-1]['price']

                    # write new trades to tradefile
                    if self.record_trades:
                        tradefile = TRADES+'{}_{}_{}'.format(
                            self.exchange, self.base, self.alt)
                        if not os.path.exists(TRADES):
                            build_data_directories()

                        with open(tradefile, 'a') as writefile:
                            writer = csv.writer(writefile, delimiter=',')
                            writer.writerow([trade['timestamp'],
                                            trade['price'], trade['amount']])

        return self.new_trades

    def run(self, update_every=15):
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
            return {'timestamp': 0}


class CandleStream(object):
    """ A CandleStream converts trade data from a TradeSource to candle data
    for a given period. Multiple candle streams can be run from the same
    TradeSource. In that case, all the CandleStreams should be updated before
    each new update of the TradeSource.
    """
    def __init__(self, tradesource, period, record_candles=True,
                 start=None, quiet=False):
        self.tradesource = tradesource
        self.p_value, self.p_unit = parse_period(period)
        self.period = period
        self.step = pdelta(self.p_value, self.p_unit)
        self.exchange, self.base, self.alt = (tradesource.exchange,
                                              tradesource.base,
                                              tradesource.alt)
        self.candlefile = CANDLES + '{}_{}_{}_{}{}'.format(
            self.exchange, self.base, self.alt, self.p_value, self.p_unit)
        self.record_candles = record_candles
        self.quiet = quiet

        # check for candle directory
        if not os.path.exists(CANDLES):
            build_data_directories()

        # check for candle file
        if os.path.exists(self.candlefile):
            with open(self.candlefile, 'rb') as readfile:
                reader = csv.reader(readfile, delimiter=',')
                if start:
                    self.closed_candles = [[int(candle[0])] + [Decimal(x)
                                           for x in candle[1:]]
                                           for candle in reader
                                           if ut_to_dt(candle[0]) < start]
                else:
                    self.closed_candles = [[int(candle[0])] + [Decimal(x)
                                           for x in candle[1:]]
                                           for candle in reader]
            self.active_candle = self.closed_candles.pop()

        # if no candle file, check for trades in tradesource
        elif self.tradesource.trades:
            if not self.quiet:
                print 'No candlefile found; generating from tradesource...'
            if start:
                self.closed_candles = [[int(candle[0])] + [Decimal(x)
                                       for x in candle[1:]]
                                       for candle in trades_to_candles(
                                           self.tradesource.trades, period)
                                       if ut_to_dt(candle[0]) < start]
            else:
                self.closed_candles = [[int(candle[0])] + [Decimal(x)
                                       for x in candle[1:]]
                                       for candle in trades_to_candles(
                                           self.tradesource.trades, period)]
            # assume the last candle is still active
            self.active_candle = self.closed_candles.pop()

        # if no candles or trades
        else:
            if not self.quiet:
                print ('No candlefile found; no tradefile found; '
                       'waiting for new trades...')
            self.closed_candles = []
            self.active_candle = []
            self.active_trades = []
            self.next_start = None

        if self.active_candle:  # at least one candle was found
            self.next_start = ut_to_dt(self.active_candle[0]) + self.step

            # assume last candle is not closed yet (check in update)
            self.last_closed_known = False

            # get trade data from most recent candle
            self.active_trades = [
                trade for trade in self.tradesource.trades
                if trade['timestamp'] >= self.active_candle[0]]

    def update(self):
        """ Checks for new trades and updates the candle data. """

        new_trades = self.tradesource.new_trades
        if new_trades:
            self.active_trades += [{'timestamp': int(trade['timestamp']),
                                    'price': Decimal(trade['price']),
                                    'amount': Decimal(trade['amount'])}
                                   for trade in new_trades]

            if not self.next_start:
                first = ut_to_dt(self.active_trades[0]['timestamp'])
                start = datetime(
                    year=first.year, month=first.month, day=first.day)
                while start + self.step < first:
                    start += self.step
                self.next_start = start + self.step
                self.active_candle = get_candle(
                    dt_to_ut(start), self.active_trades)
                self.last_closed_known = False

            # dump older trades if active candle has closed,
            # accounting for possible gaps
            while ut_to_dt(
                    self.active_trades[-1]['timestamp']) > self.next_start:
                self.dump()

            # update active candle
            new_candle = get_candle(self.active_candle[0], new_trades)
            self.active_candle = self.update_candle(
                self.active_candle, new_candle)

    def dump(self):
        """
        Run once the candle is completed, to close the candle and record
        it to the candle data file.
        """
        to_dump = [t for t in self.active_trades
                   if ut_to_dt(t['timestamp']) < self.next_start]
        to_keep = [t for t in self.active_trades
                   if ut_to_dt(t['timestamp']) >= self.next_start]

        if len(to_dump):
            if not self.quiet:
                print '{} {}{} candle closed at {} with {} trades'.format(
                    self.exchange, self.p_value, self.p_unit,
                    to_dump[-1]['price'], len(to_dump))

            dump_candle = get_candle(self.active_candle[0], to_dump)

            self.closed_candles.append(dump_candle)

            if self.record_candles:
                # if last entry not closed, pop out the last entry
                # before rewriting with update
                if not self.last_closed_known:
                    save_candlefile(self.closed_candles, self.period,
                                    self.candlefile, replace=True)
                else:
                    save_candlefile([dump_candle], self.period,
                                    self.candlefile, replace=False)

        self.active_trades = to_keep
        self.active_candle = get_candle(
            dt_to_ut(self.next_start), [to_keep[0]])

        self.next_start += self.step

        # only closed candles are saved, so last will
        # always be closed on further updates
        self.last_closed_known = True

    def update_candle(self, active_candle, new_candle):
        """ Merges new trade data with an open candle. """

        # candle order: [start, open, close, high, low, volume]
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
        return self.tradesource.trades[-1]['price']

    def get_candles(self, ncandles=None):
        if ncandles:
            return self.closed_candles[-(ncandles-1):] + [self.active_candle]
        else:
            return self.closed_candles + [self.active_candle]

    def get_closed_candles(self, ncandles=None):
        if ncandles:
            return self.closed_candles[-(ncandles-1):]
        else:
            return self.closed_candles

    # candles beginning after timestamp
    def get_candles_since(self, timestamp):
        g = itertools.dropwhile(
            lambda c: c[0] < timestamp, self.closed_candles)
        return list(g)

    # candles containing timestamp and beginning after timestamp
    def get_candles_from(self, timestamp):
        timestamp = dt_to_ut(ut_to_dt(timestamp) - self.step)
        g = itertools.dropwhile(
            lambda c: c[0] < timestamp, self.closed_candles)
        return list(g)


class ExchangeTrader(object):
    """
    The backend for the GUI-based live trading implementation.

    Because API calls can potentially fail (e.g. due to internet connection
    lapses), they are placed in a queue that is attempted with each update.
    If an API call fails, it will be retained to try again with the
    next update, and further execution of the queue will stop until the
    call succeeds and any alert messages are cleared. If it succeeds,
    it will be removed from the queue and another update will be forced.

    Strategy trade conditions will not be checked until the queue has
    cleared. If triggered, the trade orders will be added to the queue
    and a new update will be forced. If a buy is called for, a stop sell
    order will also be queued if a stoploss is specified in the Strategy.
    """
    def __init__(self, candlestream, api, strategy):

        self.candlestream = candlestream

        self.exchange, self.base, self.alt = (candlestream.exchange,
                                              candlestream.base,
                                              candlestream.alt)
        self.symbol = self.base.lower() + self.alt.lower()

        self.strategy = strategy
        self.strategy.trader = self

        self.api = api
        self.messages = []
        self.openMarketOrder = False
        self.openOrders = []

        self.queue = []

        self.queueRequery()

        # attempt first pass of queue immediately
        while self.queue:
            action = self.queue[0]
            response = action()
            if response:  # action accepted; remove from queue
                self.queue = self.queue[1:]
            else:  # action not accepted; try again next update
                break

    def getOpenOrders(self):
        """ example response:
        [{  u'avg_execution_price': u'0.0',
            u'remaining_amount': Decimal('0.27958'),
            u'timestamp': Decimal('1389409705.0'),
            u'price': Decimal('850.0'),
            u'exchange': None,
            u'executed_amount': Decimal('0.0'),
            u'symbol': u'btcusd',
            u'is_live': True,
            u'was_forced': False,
            u'id': 5475379,
            u'is_cancelled': False,
            u'original_amount': Decimal('0.27958'),
            u'type': u'exchange stop',
            u'side': u'sell'  }]
            """
        response = self.api.orders()

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            self.openOrders = response
            """
            Keep track of whether an open market order is still on the books,
            such that each update need not re-check unless the trader
            has recently placed a new trade
            """
            self.openMarketOrder = False
            for order in self.openOrders:
                if 'market' in order['type']:
                    self.openMarketOrder = True
            return True

    def getFinances(self):
        """
        Example response:
        [{u'available': Decimal('0.0'), u'currency': u'btc',
          u'amount': Decimal('0.0'), u'type': u'trading'},
         {u'available': Decimal('0.0'), u'currency': u'usd',
          u'amount': Decimal('0.0'), u'type': u'trading'},

         {u'available': Decimal('0.0'), u'currency': u'btc',
          u'amount': Decimal('0.0'), u'type': u'deposit'},
         {u'available': Decimal('0.0'), u'currency': u'usd',
          u'amount': Decimal('0.0'), u'type': u'deposit'},

         {u'available': Decimal('0.0'), u'currency': u'btc',
          u'amount': Decimal('0.0'), u'type': u'exchange'},
         {u'available': Decimal('481.24270344'), u'currency': u'usd',
          u'amount': Decimal('481.24270344'), u'type': u'exchange'}]
        """
        response = self.api.balances()

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            self.finances = {}
            for entry in response:
                orderType = entry['type']
                if orderType not in self.finances:
                    self.finances[orderType] = {
                        entry['currency']: {'available': entry['available'],
                                            'amount': entry['amount']}}
                else:
                    self.finances[orderType][entry['currency']] = {
                        'available': entry['available'],
                        'amount': entry['amount']}
            return True

    def getCompletedTrades(self, weeks=4):
        """ Example response:
        {u'timestamp': Decimal('1386924359.0'),
         u'price': Decimal('906.19'),
         u'type': u'Buy',
         u'amount': Decimal('0.6605'),
         u'exchange': u'bitstamp'}
         """
        now = datetime.utcnow()
        start = dt_to_ut(now - timedelta(weeks=weeks))
        payload = {'symbol': self.base+self.alt, 'timestamp': start}
        response = self.api.past_trades(payload)

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            self.my_trades = response[::-1]
            return True

    def getMarketPrice(self, action=None):
        response = self.api.book({'limit_bids': 5, 'limit_asks': 5},
                                 symbol=self.symbol)

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            bids, asks = response['bids'], response['asks']
            prices = {'Buy': asks[0]['price'], 'Sell': bids[0]['price']}
            if not action:
                return prices
            else:
                return prices[action]

    def getEquity(self):
        alt = self.finances['exchange'][self.alt]['amount']
        base = self.finances['exchange'][self.base]['amount']
        return alt + base * self.getMarketPrice('Sell')

    def equity(self):
        alt = self.finances['exchange'][self.alt]['amount']
        base = self.finances['exchange'][self.base]['amount']
        return alt + base * self.lastPrice()

    def lastPrice(self):
        return self.candlestream.price()

    def position(self):
        if self.my_trades[-1]['type'] == 'Buy':
            position = 'long'
        elif self.my_trades[-1]['type'] == 'Sell':
            position = 'out'
        return position

    def marketTradeEstimate(self, amount, action):
        """ For 'Buy' action, returns cost of buying amount. For 'Sell' action,
        returns revenue of selling amount (accounting for open orders)
        """
        response = self.api.book({'limit_bids': 5, 'limit_asks': 5},
                                 symbol=self.symbol)

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            bids, asks = response['bids'], response['asks']

            if action == 'Buy':
                orders = asks
            if action == 'Sell':
                orders = bids

            remaining = Decimal(amount)
            result = Decimal(0)
            for order in orders:
                if order['amount'] > remaining:
                    result += remaining*order['price']
                    break
                else:
                    result += order['amount']*order['price']
                    remaining -= order['amount']
            return result

    def placeOrder(self, action, amount='all',
                   orderType='exchange market', price=None):
        """
        Example response:
       {u'avg_execution_price': u'0.0',
        u'remaining_amount': Decimal('0.1'),
        u'order_id': 5480291,
        u'timestamp': Decimal('1389414906.0'),
        u'price': Decimal('864.01'),
        u'exchange': u'bitfinex',
        u'executed_amount': Decimal('0.0'),
        u'symbol': u'btcusd',
        u'is_live': True,
        u'was_forced': False,
        u'id': 5480291,
        u'is_cancelled': False,
        u'original_amount': Decimal('0.1'),
        u'type': u'exchange market',
        u'side': u'sell'}
        """
        print ('placeOrder triggered with action {}, amount {}, type {} '
               'and price {}').format(action, amount, orderType, price)
        if not price:
            price = self.getMarketPrice(action)
            if price:
                print ('price not provided; '
                       'market price of {} used').format(price)
            else:
                print 'price not provided; market price could not be obtained'
                return

        if amount in ['all', 'All']:
            if action == 'Sell':
                amount = self.finances['exchange'][self.base]['available']
                print '{} sell all attempted with order amount {}'.format(
                    orderType, amount)
        payload = {'symbol': self.symbol,
                   'amount': amount,
                   'price': price,
                   'exchange': self.exchange,
                   'side': action.lower(),
                   'type': orderType}

        response = self.api.order_new(payload)

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            if 'market' in orderType:
                self.openMarketOrder = True
            print 'placeOrder successful'
            return response

    def cancelOrder(self, order_id):
        payload = {'order_id': order_id}
        response = self.api.order_cancel(payload)

        # check response
        if response is None:
            return
        elif 'message' in response:
            self.messages.append(response['message'])
            return
        else:
            return response

    def queueRequery(self):
        self.queue.append(lambda: self.getOpenOrders())
        self.queue.append(lambda: self.getFinances())
        self.queue.append(lambda: self.getCompletedTrades())

    def exitPoint(self, reference='peak'):
        """ Calculates exit price points based on stoploss value specified by
        Strategy.set_stoploss().
        """
        if reference == 'entry':
            # calculate stoploss relative to entry price
            if self.my_trades:
                if self.position() == 'long':
                    entry_price = self.my_trades[-1]['price']
                    return entry_price - (entry_price*self.strategy.stoploss)

        if reference == 'peak':
            # calculate stoploss relative to peak closing price since entry
            if self.my_trades:
                if self.position() == 'long':
                    entry_price = self.my_trades[-1]['price']
                    timestamp = self.my_trades[-1]['timestamp']
                    candles_from = self.candlestream.get_candles_from(
                        timestamp)
                    max_from = Decimal(max([entry_price] + [c[2]
                                       for c in candles_from]))
                    return max_from - (max_from*self.strategy.stoploss)

    def lastTradeType(self):
        if self.my_trades:
            return self.my_trades[-1]['type']

    def update(self):
        actionTaken = False  # default case

        # cease updating if alert messages haven't been dismissed
        if self.messages:
            return {'messages': self.messages}

        # if a market order was placed recently, requery
        if self.openMarketOrder:
            if not self.getOpenOrders():
                # query failed; try again next update
                return actionTaken

        self.openMarketOrder = False  # default case
        for order in self.openOrders:
            if 'market' in order['type']:
                # order still open; wait until next update and check again
                self.openMarketOrder = True
                print 'open market order detected; waiting for next update'
                return actionTaken

        # ATTEMPT TO PROCESS QUEUE
        if self.queue:
            action = self.queue[0]
            response = action()
            if response:  # action accepted; remove from queue and force update
                self.queue = self.queue[1:]
                actionTaken = True
                self.update()
                return actionTaken
            else:  # action failed; try again next update
                return actionTaken

        if self.position() == 'long':
            # check if expected stoploss is missing
            # or stop order should be increased
            missing = True  # default case
            for order in self.openOrders:
                if order['side'] == 'sell' and 'stop' in order['type']:
                    # stop order is present
                    missing = False

                    # check if price increase is called for
                    current_exit = order['price']
                    new_exit = self.exitPoint()
                    if new_exit > current_exit:
                        print ('exit point has increased from {} to {} '
                               'since stop order placed; resubmitting stop '
                               'order').format(current_exit, new_exit)
                        # cancel current stop order
                        self.queue.append(
                            lambda: self.cancelOrder(order['id']))
                        self.queueRequery()
                        # post new stop order at higher price
                        self.queue.append(lambda: self.placeOrder(
                            'Sell', orderType='exchange stop', price=new_exit))
                        self.queueRequery()
                        return actionTaken

            if missing and 'stop' not in self.lastTradeType():
                print 'stoploss is missing; queuing stop order'
                self.queue.append(
                    lambda: self.placeOrder('Sell', orderType='exchange stop',
                                            price=self.exitPoint()))
                self.queueRequery()
                return actionTaken

        # check if price has passed stoploss
        for order in self.openOrders:
            if order['side'] == 'sell' and 'stop' in order['type']:
                # stop sell order is present; check new trades
                new_trades = self.candlestream.tradesource.new_trades
                for trade in new_trades:
                    if trade['price'] < order['price']:
                        # assume stop order triggered, requery API
                        print 'price below stoploss detected; requerying'
                        self.queueRequery()
                        return actionTaken

        # CHECK CONDITIONS FOR NEW TRADES
        action = self.strategy.check(
            position=self.position(), my_trades=self.my_trades,
            candlestream=self.candlestream)  # **kwargs
        if action:
            # queue trade and force update
            print 'action {} received'.format(action)
            self.queue.append(lambda: self.trade(action))
            return actionTaken or self.update()

    def trade(self, action, amount=None):
        # buy action
        if action == 'Buy':
            if not amount:
                price = self.getMarketPrice(action)
                dollars_at_risk = self.strategy.risk * self.equity()
                price_move = price * self.strategy.stoploss

                # buy amount based on risk management
                amount = (dollars_at_risk / price_move *
                          (1 - self.strategy.commission))
                print 'buy amount ', amount

            cost = self.marketTradeEstimate(amount, action)
            print 'buy cost ', cost

            # make sure query executed
            if cost is None:
                return
            # make sure sufficient finances are available
            elif cost > self.finances['exchange'][self.alt]['available']:
                self.messages.append(
                    'WARNING: cost of buy exceeds available finances.')
                return

            # queue market buy order and requery
            print 'queuing market buy order'
            self.queue.append(lambda: self.placeOrder('Buy', amount=amount))
            self.queueRequery()

            # queue stop sell order and requery
            # using same amount here causes 'not enough balance'
            # error due to commission loss
            print 'queuing stop sell order'
            self.queue.append(
                lambda: self.placeOrder('Sell', orderType='exchange stop',
                                        price=self.exitPoint()))
            self.queueRequery()

            return True

        # sell action
        elif action == 'Sell':
            # close open stop sell orders
            for order in self.openOrders:
                if 'stop' in order['type'] and 'sell' in order['side']:
                    print 'queuing cancel of open stop order'
                    self.queue.append(lambda: self.cancelOrder(order['id']))
                    self.queueRequery()

            if not amount:
                amount = 'all'

            # queue market order and requery
            print 'queuing market sell order'
            self.queue.append(lambda: self.placeOrder(action, amount=amount))
            self.queueRequery()

            return True
