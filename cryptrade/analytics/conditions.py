from __future__ import division
import itertools
import numpy as np


class Condition(object):
    """ Base class for defining conditions at which trades should be executed.
    Basically, it stores a function to be evaluated later (when check() is
    called). Conditions can be added in order to create AND relationships and
    subtracted to create AND NOT relationships.

    A Condition is instantiated with a custom function to be evaluated later
    when Condition.check() is called. Since trading strategies may involve
    many considerations (recent trades, current position, particular sets of
    candles, even other Conditions...), the check() expects only **kwargs,
    which are passed directly to the stored function. As such, the function
    should always accept **kwargs in addition to the specific args needed for
    its own execution.

    The ExchangeTrader in trading.py used by the live trading GUI currently
    passes position, my_trades, and candlestream kwargs in its update calls.

    AND and AND NOT relationships between Conditions are achieved using
    arithmetic operators, e.g. for conditions A and B,

        A + B yields a new Condition which represents A AND B
        A - B yields a new Condition which represents A AND NOT B

    A and B may expect different arguments, but when check() is called,
    it should be passed keywords accounting for all the arguments expected
    by either A and B.
    """
    def __init__(self, function):
        # function to be checked
        self.function = function

    def check(self, **kwargs):
        return self.function(**kwargs)

    def __add__(self, other):
        return Condition(lambda **kwargs:
                         self.function(**kwargs) and other.function(**kwargs))

    def __radd__(self, other):
        return Condition(lambda **kwargs:
                         self.function(**kwargs) and other.function(**kwargs))

    def __sub__(self, other):
        return Condition(lambda **kwargs:
                         self.function(**kwargs)
                         and not other.function(**kwargs))


class GreaterThan(Condition):
    """ Condition which compares the most recent values of two indicators,
    used e.g. in moving average crossover strategies. Rather than
    specifically detecting the point of crossover, this evaluates the
    current trend, thus producing trade signals even after the point of
    crossover. Should generally be combined with a position Condition such
    that trade signals are only processed if the position is out of sync with
    the trend.
    """
    def __init__(self, indicator1, indicator2):
        """ The indicators to be compared should be passed in the order of
        the operator, e.g. indicator1 > indicator2 will be evaluated on check.
        """
        def checkfunc(candlestream=None, candles=None, **kwargs):
            if candlestream:  # assume live trader
                candles = candlestream.get_closed_candles(ncandles=200)
                values1 = indicator1.calculate(candles)
                values2 = indicator2.calculate(candles)
            elif candles:  # assume backtest
                values1 = indicator1.calculate(candles)
                print values1
                values2 = indicator2.calculate(candles)
                print values2
            return values1[-1] > values2[-1]

        super(GreaterThan, self).__init__(checkfunc)


class LongPosition(Condition):
    """ Simple Condition for checking position == 'long'.
    """
    def __init__(self):
        """ When check is called, it expects kwarg 'position'.
        """
        def checkfunc(position=None, **kwargs):
            if position == 'long':
                return True

        super(LongPosition, self).__init__(checkfunc)


class RecentStoploss(Condition):
    """ When a stoploss sell is triggered on a trend-following strategy,
    the trend usually continues to give a 'buy' signal for several candles
    even if the price continues to decline. Such immediate buyback is not
    generally desirable. The purpose of this condition is to block buy
    signals when there is a recent stoploss and certain buyback conditions
    are not met.

    There are two types of buyback criteria.

        The first is the occurrence of at least one trend change since the
        stoploss, e.g. the price drop eventually turned into a downtrend.
        Any new buy signals after this would mean a new uptrend has begun,
        so the stoploss should no longer be relevant.

        The second is a price rebound. Consider the case where a stoploss
        is triggered but the price rebounds before a downtrend begins,
        such that the original uptrend continues and a trend change is never
        detected. The stoploss in this case was a 'false alarm,' so buyback
        is reenabled if a price rebound persists for a given number of candles.
    """
    def __init__(self, trend_condition, candle_limit=2):
        """ trend_condition is a Condition instance describing the trend
        being traded, e.g. a GreaterThan condition comparing two moving
        averages. This is checked for trend changes since the stoploss.

        candle_limit is the integer number of candles that should sustain a
        closing price above the stoploss exit price before the price is
        considered rebounded and a buyback is enabled.

        When check is called, it expects kwargs 'my_trades' and 'candlestream'.
        """
        def checkfunc(my_trades=None, candlestream=None, **kwargs):
            verbose = False  # for debug
            if verbose:
                print 'checking stoploss blocking...'

            if my_trades and 'stop' in my_trades[-1]['type']:
                if verbose:
                    print 'last trade was stoploss'

                # get closed candles from stoploss trade onward, and exit price
                candles_from = candlestream.get_candles_from(
                    my_trades[-1]['timestamp'])
                exit_price = my_trades[-1]['price']

                # check if trend has changed since stoploss
                checks = []
                recent_candles = candlestream.get_closed_candles(ncandles=200)
                for i in range(len(candles_from)):
                    # step through candles_from, but pass enough recent_candles
                    # to check() for indicator calculation
                    candles = recent_candles[:-len(candles_from)+i]
                    checks.append(trend_condition.check(candles=candles))
                    # save results of all checks and then see
                    # if they split into multiple trends
                g = itertools.groupby(checks)
                groups = [(key, list(group)) for key, group in g]
                if verbose:
                    print len(groups), 'groups'
                    for key, grp in groups:
                        print key
                        print grp, '\n'

                if len(groups) > 1:
                    if verbose:
                        print 'trend changed since stoploss; buying enabled'
                    return False
                else:
                    if verbose:
                        print ('trend has not changed since stoploss; '
                               'checking reentry condition...')
                        print ('np.array([float(candle[2]) for candle '
                               'in candles_from[-z:]]), exit_price:\n')
                        print ('    ', np.array([float(candle[2]) for candle
                               in candles_from[-candle_limit:]]), exit_price)

                    if len(candles_from) >= candle_limit:
                        # enough candle periods have occurred since stoploss
                        # to meet or exceed the limit
                        if verbose:
                            print ('{} candles have occurred '
                                   'since stoploss, meeting '
                                   'the limit').format(len(candles_from))
                        limit_prices = [float(candle[2]) for candle
                                        in candles_from[-candle_limit:]]
                        if (np.array(limit_prices) > exit_price).all():
                            # price has rebounded for at least candle_limit
                            # closes in a row since stoploss
                            if verbose:
                                print ('price has rebounded above previous '
                                       'exit for at least {} candles; '
                                       'buying enabled').format(candle_limit)
                            return False
                        elif verbose:
                            print ('price has not rebounded '
                                   'for the last {} candles; '
                                   'buying disabled').format(len(candles_from))
                    else:
                        if verbose:
                            print ("price hasn't rebounded; "
                                   "blocking buy attempts")
                        return True
            else:
                if verbose:
                    print 'last trade was not a stoploss'
                return False

        return super(RecentStoploss, self).__init__(checkfunc)
