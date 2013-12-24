""" Tools for API access. Currently, only Bitfinex supported (includes data from Bitstamp). 
Based on sample code by Raphael Nicolle (https://community.bitfinex.com/showwiki.php?title=Sample+API+Code). """

from decimal import Decimal
import requests
import json
import base64
import hmac
import hashlib
import time
import types


def decimalize(obj, keys):
    if isinstance(obj, types.ListType):
        return [decimalize(xs, keys) for xs in obj]
    if not isinstance(obj, types.DictType):
        return obj
    #print obj
    def to_decimal(k, val):
        if val == None:
            return None
        if isinstance(val, types.ListType):
            return [decimalize(ys, keys) for ys in val]
        if k in keys:
            return Decimal(val)
        return val
    return { k: to_decimal(k, obj[k]) for k in obj }


def undecimalize(obj):
    if isinstance(obj, types.ListType):
        return map(undecimalize, obj)
    if not isinstance(obj, types.DictType):
        return obj
    #print obj
    def from_decimal(val):
        if isinstance(val, Decimal):
            return str(val)
        return val
    return { k: from_decimal(obj[k]) for k in obj }


class BitfinexAPI(object):
    def __init__(self):
        self.BITFINEX = 'api.bitfinex.com/'
        self.EXCHANGES = ['bitfinex', 'bitstamp']
        self.DECIMAL_KEYS = set(['amount', 'ask', 'available', 'bid', 'close', 'executed_amount', 
                    'high', 'highest', 'last_price', 'low', 'lowest', 'mid', 'open', 
                    'original_amount', 'price', 'remaining_amount', 'timestamp', 'volume'])
                    
    
    def ticker(self, symbol="btcusd"):
        """Gives innermost bid and asks and information on the most recent trade.
        Response:
            mid (price): (bid + ask) / 2
            bid (price): Innermost bid.
            ask (price): Innermost ask.
            last_price (price) The price at which the last order executed.
            timestamp (time) The timestamp at which this information was valid."""
        r = requests.get("https://"+self.BITFINEX+"/v1/ticker/"+symbol, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def today(self, symbol="btcusd"):
        """Today's low, high and volume.
        Response:
            low (price)
            high (price)
            volume (price)"""
        r = requests.get("https://"+self.BITFINEX+"/v1/today/"+symbol, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def candles(self, payload, symbol="btcusd"):
        """Get a list of the most recent candlesticks (trading data) for the given symbol.
        Request:
            timestamp (time): Optional. Only show trades at or after this timestamp.
        Response:
            An array of dictionaries
            start_at (timestamp)
            period (integer, period in seconds)
            open (price)
            close (price)
            highest (price)
            lowest (price)
            volume (decimal)"""
        headers = self._prepare_payload(False, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/candles/"+symbol, headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def lendbook(self, payload, symbol="btcusd"):
        """Get the full lend book.
        Request:
            limit_bids (int): Optional. Limit the number of bids (loan demands) returned. May be 0 in which case the array of bids is empty. Default is 50. 
            limit_asks (int): Optional. Limit the number of asks (loan offers) returned. May be 0 in which case the array of asks is empty. Default is 50. 
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
            timestamp (time)"""
        headers = self._prepare_payload(False, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/lendbook/"+symbol, headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def book(self, payload, symbol="btcusd"):
        """Get the full order book.
        Request:
            limit_bids (int): Optional. Limit the number of bids returned. May be 0 in which case the array of bids is empty. Default is 50. 
            limit_asks (int): Optional. Limit the number of asks returned. May be 0 in which case the array of asks is empty. Default is 50. 
        Response:
            bids (array)
            price (price)
            amount (decimal)
            timestamp (time)
            asks (array)
            price (price)
            amount (decimal)
            timestamp (time)"""
        headers = self._prepare_payload(False, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/book/"+symbol, headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def trades(self, payload, symbol="btcusd"):
        """Get a list of the most recent trades for the given symbol.
        Request:
            timestamp (time): Optional. Only show trades at or after this timestamp.
            limit_trades (int): Optional. Limit the number of trades returned. Must be >= 1. Default is 50.
        Response:
            An array of dictionaries
            price (price)
            amount (decimal)
            timestamp (time)
            exchange (string)"""
        headers = self._prepare_payload(False, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/trades/"+symbol, headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def lends(self, payload, symbol="btcusd"):
        """Get a list of the most recent lending data for the given currency: total amount lent and rate (in % by 365 days).
        Request:
            timestamp (time): Optional. Only show trades at or after this timestamp.
            limit_lends (int): Optional. Limit the number of lends returned. Must be >= 1. Default is 50.
        Response:
            An array of dictionaries
            rate (decimal, % by 365 days): Average rate of total loans opened at fixed rates
            amount_lent (decimal): Total amount of open loans in the given currency
            timestamp (time)"""
        headers = self._prepare_payload(False, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/lends/"+symbol, headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def symbols(self):
        """Get a list of valid symbol IDs.
        Response:
            A list of symbol names. Currently just "btcusd"."""
        r = requests.get("https://"+self.BITFINEX+"/v1/symbols", verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)



### AUTHENTICATED ###
    def order_new(self, payload):
        """Submit a new order.
        Request:
            symbol (string): The name of the symbol (see `/symbols`).
            amount (decimal): Order size: how much to buy or sell.
            price (price): Price to buy or sell at. May omit if a market order.
            exchange (string): "bitfinex", "bitstamp", "all" (for no routing).
            side (string): Either "buy" or "sell".
            type (string): Either "market" / "limit" / "stop" / "trailing-stop" / "exchange market" / "exchange limit" / "exchange stop" / "exchange trailing-stop". (type starting by "exchange " are exchange orders, others are margin trading orders= 
            is_hidden (bool) true if the order should be hidden. Default is false.
        Response:
            order_id (int): A randomly generated ID for the order.
            and the information given by /order/status
        Order types:
            Margin trading type	    Exchange type
            LIMIT	                EXCHANGE LIMIT
            MARKET	                EXCHANGE MARKET
            STOP	                EXCHANGE STOP
            TRAILING STOP	        EXCHANGE TRAILING STOP"""
        payload["request"] = "/v1/order/new"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        r = requests.post("https://"+self.BITFINEX+"/v1/order/new", headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def order_cancel(self, payload):
        """Cancel an order.
        Request:
            order_id (int): The order ID given by `/order/new`.
        Response:
            Result of /order/status for the cancelled order."""
        payload["request"] = "/v1/order/cancel"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        r = requests.post("https://"+self.BITFINEX+"/v1/order/cancel", headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def order_status(self, payload):
        """Get the status of an order. Is it active? Was it cancelled? To what extent has it been executed? etc.
        Request:
            order_id (int): The order ID given by `/order/new`.
        Response:
            symbol (string): The symbol name the order belongs to.
            exchange (string): "bitfinex", "mtgox", "bitstamp".
            price (decimal): The price the order was issued at (can be null for market orders).
            avg_execution_price (decimal): The average price at which this order as been executed so far. 0 if the order has not been executed at all. side (string): Either "buy" or "sell".
            type (string): Either "market" / "limit" / "stop" / "trailing-stop".
            timestamp (time): The timestamp the order was submitted.
            is_live (bool): Could the order still be filled?
            is_cancelled (bool): Has the order been cancelled?
            was_forced (bool): For margin only: true if it was forced by the system.
            executed_amount (decimal): How much of the order has been executed so far in its history?
            remaining_amount (decimal): How much is still remaining to be submitted?
            original_amount (decimal): What was the order originally submitted for?"""
        payload["request"] = "/v1/order/status"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/order/status", headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def orders(self):
        payload = {}
        payload["request"] = "/v1/orders"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/orders", headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)


    def balances(self):
        payload = {}
        payload["request"] = "/v1/balances"
        payload["nonce"] = str(long(time.time() * 100000))
        headers = self._prepare_payload(True, payload)
        r = requests.get("https://"+self.BITFINEX+"/v1/balances", headers=headers, verify=False)
        return decimalize(r.json(), self.DECIMAL_KEYS)




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
