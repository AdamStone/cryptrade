""" Batch create candle data files from historical trade data for many candles.
Warning: this may take a long time for large trade files! """

import cryptrade

markets = ['bitfinex_BTC_USD', 'bitstamp_BTC_USD']#, 'mtgox_BTC_USD', 'btce_BTC_USD', 'btcn_BTC_CNY'] 

periods = ['1m', '5m', '10m', '15m', '30m', '1h', '2h', '6h', '12h', '24h']

for period in periods:
    for market in markets:
        print 'Processing {}, {} candles'.format(market, period)
        candles = cryptrade.tradefile_to_candles(market, period)
        cryptrade.save_candlefile(candles, period, market)