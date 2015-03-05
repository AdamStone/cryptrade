""" Tools for API access. Currently, only Bitfinex supported
(includes data from Bitstamp). Based on sample code by Raphael Nicolle
(https://community.bitfinex.com/showwiki.php?title=Sample+API+Code). """

from decimal import Decimal, getcontext
getcontext().prec = 8
import requests
import json
import simplejson
import base64
import hmac
import ssl
import hashlib
import time
import types
import httplib

import traceback

TIMEOUT = 5


def decimalize(obj, keys):
    if isinstance(obj, types.ListType):
        return [decimalize(xs, keys) for xs in obj]
    if not isinstance(obj, types.DictType):
        return obj

    def to_decimal(k, val):
        if val is None:
            return None
        if isinstance(val, types.ListType):
            return [decimalize(ys, keys) for ys in val]
        if k in keys:
            return Decimal(val)
        return val
    return {k: to_decimal(k, obj[k]) for k in obj}


def undecimalize(obj):
    if isinstance(obj, types.ListType):
        return map(undecimalize, obj)
    if not isinstance(obj, types.DictType):
        return obj

    def from_decimal(val):
        if isinstance(val, Decimal):
            return str(val)
        return val
    return {k: from_decimal(obj[k]) for k in obj}


class BitfinexAPI(object):
    def __init__(self):
        self.BITFINEX = 'api.bitfinex.com/'
        self.EXCHANGES = ['bitfinex', 'bitstamp']
        self.DECIMAL_KEYS = set([
            'amount', 'ask', 'available', 'bid', 'close', 'executed_amount',
            'high', 'highest', 'last_price', 'low', 'lowest', 'mid', 'open',
            'original_amount', 'price', 'remaining_amount', 'timestamp',
            'volume'])

    def tryAPIcall(self, func):
        try:
            r = func()
            return decimalize(r.json(), self.DECIMAL_KEYS)
        except requests.ConnectionError:
            print 'Connection error'
            return
        except requests.Timeout:
            print 'Request timed out'
            return
        except simplejson.decoder.JSONDecodeError:
            print 'JSON decode error'
            return
        except ssl.SSLError:
            print 'SSL error'
            return
        except httplib.IncompleteRead:
            print 'Incomplete read error'
            return
        except:
            traceback.print_exc()
            return

    def ticker(self, symbol="btcusd"):
        """
        Gives innermost bid and asks and information on the most recent trade.

        Response:
            mid (price): (bid + ask) / 2
            bid (price): Innermost bid.
            ask (price): Innermost ask.
            last_price (price) The price at which the last order executed.
            timestamp (time) The timestamp at which this
                information was valid.
        """
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/ticker/"+symbol,
                                 verify=False, timeout=TIMEOUT))

    def today(self, symbol="btcusd"):
        """
        Today's low, high and volume.

        Response:
            low (price)
            high (price)
            volume (price)
        """
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/today/"+symbol,
                                 verify=False, timeout=TIMEOUT))

    def candles(self, payload, symbol="btcusd"):
        """
        Get a list of the most recent candlesticks
        (trading data) for the given symbol.

        Request:
            timestamp (time): Optional. Only show trades at or
                after this timestamp.
        Response:
            An array of dictionaries
            start_at (timestamp)
            period (integer, period in seconds)
            open (price)
            close (price)
            highest (price)
            lowest (price)
            volume (decimal)
        """
        headers = self._prepare_payload(False, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/candles/" +
                                 symbol, headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def lendbook(self, payload, symbol="btcusd"):
        """
        Get the full lend book.

        Request:
            limit_bids (int): Optional. Limit the number of bids (loan
                demands) returned. May be 0 in which case the array of
                bids is empty. Default is 50.
            limit_asks (int): Optional. Limit the number of asks (loan
                offers) returned. May be 0 in which case the array of
                asks is empty. Default is 50.
        Response:
            bids (array of loan demands):
            rate (rate in % per 365 days)
            amount (decimal)
            period (days): minimum period for the loan
            timestamp (time)
            asks (array of loan offers)
            rate (rate in % per 365 days)
            amount (decimal)
            period (days): maximum period for the loan
            timestamp (time)
        """
        headers = self._prepare_payload(False, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/lendbook/" +
                                 symbol, headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def book(self, payload, symbol="btcusd"):
        """
        Get the full order book.

        Request:
            limit_bids (int): Optional. Limit the number of bids returned. May
                be 0 in which case the array of bids is empty. Default is 50.
            limit_asks (int): Optional. Limit the number of asks returned. May
                be 0 in which case the array of asks is empty. Default is 50.
        Response:
            bids (array)
            price (price)
            amount (decimal)order_cancel
            timestamp (time)
            asks (array)
            price (price)
            amount (decimal)
            timestamp (time)
        Example:
            {u'bids':
                [{u'timestamp': Decimal('1389375876.0'),
                  u'price': Decimal('830.0'),
                  u'amount': Decimal('0.71413304')},
                 {u'timestamp': Decimal('1389375863.0'),
                  u'price': Decimal('829.0'), u'amount': Decimal('1.0')},
                 {u'timestamp': Decimal('1389376067.0'),
                  u'price': Decimal('829.0'), u'amount': Decimal('2.0')},
                 {u'timestamp': Decimal('1389376072.0'),
                  u'price': Decimal('828.01'),
                  u'amount': Decimal('0.81391621')},
                 {u'timestamp': Decimal('1389375637.0'),
                  u'price': Decimal('828.0'), u'amount': Decimal('1.0')}],
             u'asks':
                 [{u'timestamp': Decimal('1389376082.0'),
                   u'price': Decimal('831.0'),
                   u'amount': Decimal('0.74827024')},
                  {u'timestamp': Decimal('1389376064.0'),
                   u'price': Decimal('831.01'),
                   u'amount': Decimal('4.08318334')},
                  {u'timestamp': Decimal('1389376090.0'),
                   u'price': Decimal('831.01'), u'amount': Decimal('0.4')},
                  {u'timestamp': Decimal('1389376089.0'),
                   u'price': Decimal('832.8799'), u'amount': Decimal('1.35')},
                  {u'timestamp': Decimal('1389376082.0'),
                   u'price': Decimal('832.88'),
                   u'amount': Decimal('0.83139194')}]
            }
        """
        headers = self._prepare_payload(False, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/book/"+symbol,
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def trades(self, payload, symbol="btcusd"):
        """
        Get a list of the most recent trades for the given symbol.

        Request:
            timestamp (time): Optional. Only show trades at
                or after this timestamp.
            limit_trades (int): Optional. Limit the number of trades
                returned. Must be >= 1. Default is 50.
        Response:
            An array of dictionaries
            price (price)
            amount (decimal)
            timestamp (time)
            exchange (string)
        """
        headers = self._prepare_payload(False, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/trades/"+symbol,
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def lends(self, payload, symbol="btcusd"):
        """
        Get a list of the most recent lending data for the given currency:
        total amount lent and rate (in % by 365 days).

        Request:
            timestamp (time): Optional. Only show trades at or
                after this timestamp.
            limit_lends (int): Optional. Limit the number of lends returned.
                Must be >= 1. Default is 50.
        Response:
            An array of dictionaries
            rate (decimal, % by 365 days): Average rate of total
                loans opened at fixed rates
            amount_lent (decimal): Total amount of open loans
                in the given currency
            timestamp (time)
        """
        headers = self._prepare_payload(False, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/lends/"+symbol,
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def symbols(self):
        """
        Get a list of valid symbol IDs.

        Response:
            A list of symbol names. Currently just "btcusd".
        """
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/symbols",
                                 verify=False))

### AUTHENTICATED ###
    def order_new(self, payload):
        """
        Submit a new order.

        Request:
            symbol (string): The name of the symbol (see `/symbols`).
            amount (decimal): Order size: how much to buy or sell.
            price (price): Price to buy or sell at. May omit if a market order.
            exchange (string): "bitfinex", "bitstamp", "all" (for no routing).
            side (string): Either "buy" or "sell".
            type (string): "market" / "limit" / "stop" / "trailing-stop" /
                "exchange market" / "exchange limit" / "exchange stop" /
                "exchange trailing-stop". (type starting by "exchange " are
                exchange orders, others are margin trading orders)
            is_hidden (bool): true if the order should be hidden.
                Default is false.
        Response:
            order_id (int): A randomly generated ID for the order.
            and the information given by /order/status
        Order types:
            Margin trading type     Exchange type
            LIMIT                   EXCHANGE LIMIT
            MARKET                  EXCHANGE MARKET
            STOP                    EXCHANGE STOP
            TRAILING STOP           EXCHANGE TRAILING STOP
        Example Response:
           {u'avg_execution_price': u'0.0',
            u'remaining_amount': Decimal('0.1'),
            u'order_id': 5480291,
            u'timestamp': Decimal('1389414906.469904775'),
            u'price': Decimal('864.01'),
            u'exchange': u'bitfinex',
            u'executed_amount': Decimal('0.0'),
            u'symbol': u'btcusd',
            u'is_live': True,
            u'was_forced': False,
            u'id': 5480291,
            u'is_cancelled': False,
            u'original_amount': Decimal('0.1'),
            u'type': u'exchange market', u'side': u'sell'}
        """

        payload["request"] = "/v1/order/new"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.post("https://"+self.BITFINEX+"/v1/order/new",
                                  headers=headers, verify=False,
                                  timeout=TIMEOUT))

    def order_cancel(self, payload):
        """
        Cancel an order.

        Request:
            order_id (int): The order ID given by `/order/new`.
        Response:
            Result of /order/status for the cancelled order."""
        payload["request"] = "/v1/order/cancel"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.post("https://"+self.BITFINEX+"/v1/order/cancel",
                                  headers=headers, verify=False,
                                  timeout=TIMEOUT))

    def order_status(self, payload):
        """
        Get the status of an order. Is it active? Was it cancelled?
        To what extent has it been executed? etc.

        Request:
            order_id (int): The order ID given by `/order/new`.
        Response:
            symbol (string): The symbol name the order belongs to.
            exchange (string): "bitfinex", "mtgox", "bitstamp".
            price (decimal): The price the order was issued at (can be
                null for market orders).
            avg_execution_price (decimal): The average price at which
                this order as been executed so far.
                0 if the order has not been executed at all.
            side (string): Either "buy" or "sell".
            type (string): "market" / "limit" / "stop" / "trailing-stop".
            timestamp (time): The timestamp the order was submitted.
            is_live (bool): Could the order still be filled?
            is_cancelled (bool): Has the order been cancelled?
            was_forced (bool): For margin only: true if it was
                forced by the system.
            executed_amount (decimal): How much of the order has
                been executed so far in its history?
            remaining_amount (decimal): How much is still
                remaining to be submitted?
            original_amount (decimal): What was the order
                originally submitted for?
        """
        payload["request"] = "/v1/order/status"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/order/status",
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def orders(self):
        """
        An array of the results of `/order/status` for all your live orders.
        Example Response:
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

        payload = {}
        payload["request"] = "/v1/orders"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/orders",
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def positions(self):
        """ View your active positions. """

        payload = {}
        payload["request"] = "/v1/positions"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/positions",
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def balances(self):
        """
        A list of wallet balances:
            type (string): "trading", "deposit" or "exchange"
            currency (string): Currency
            amount (decimal): How much balance of this currency in this wallet
            available (decimal): How much X there is in this wallet that
                is available to trade.

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

        payload = {}
        payload["request"] = "/v1/balances"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.get("https://"+self.BITFINEX+"/v1/balances",
                                 headers=headers, verify=False,
                                 timeout=TIMEOUT))

    def past_trades(self, payload):
        """
        Cancel an order.

        Request:
            symbol (string): The pair traded (BTCUSD, LTCUSD, LTCBTC).
            timestamp (time): Trades made before this timestamp won't
                be returned.
            limit_trades (int): Optional. Limit the number of trades
                returned. Default is 50.
        Response:
            A list of dictionaries:
            price (price)
            amount (decimal)
            timestamp (time)
            exchange (string)
            type (string) Sell or Buy
        """
        payload["request"] = "/v1/mytrades"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        return self.tryAPIcall(
            lambda: requests.post("https://"+self.BITFINEX+"/v1/mytrades",
                                  headers=headers, verify=False,
                                  timeout=TIMEOUT))

    # Private
    def _prepare_payload(self, should_sign, d):
        j = json.dumps(undecimalize(d))
        data = base64.standard_b64encode(j)

        if should_sign:
            h = hmac.new(self.secret, data, hashlib.sha384)
            signature = h.hexdigest()

            return {
                "X-BFX-APIKEY": self.key,
                "X-BFX-SIGNATURE": signature,
                "X-BFX-PAYLOAD": data,
            }
        else:
            return {
                "X-BFX-PAYLOAD": data,
            }
