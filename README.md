cryptrade
=========

Cryptrade is a cryptocurrency market visualization and automated trading 
program written in python, with the aim of supporting collection and 
plotting of live trade data, batch backtesting of trading strategies, 
live trading simulation, and automated live trading. Current development 
is focused on the Bitfinex exchange. 

This (pre)release includes a very limited implementation:

    Live monitoring and visualization of the Bitfinex BTC/USD market
    Automated live trading (experimental) of the Bitfinex BTC/USD market
    Moving average crossover trading strategies with stoploss and risk management

For now only the Bitfinex API is supported. 

A batch backtesting framework is in progress.


Dependencies
-------------

NumPy, MatPlotLib, Requests, and PyQt4


Getting Started
-------------

An installer is not yet implemented; scripts can be run from the same 
directory as the cryptrade package, or the cryptrade package can be
placed in the python path. A data directory will be created where the 
scripts are run if they are set to record trade and candle data.

Example 1 demonstrates how to start a simple live trade monitor that 
records and prints new trades in the terminal window as they come in 
from the exchange. 

Example 2 demonstrates how to start the GUI, which provides a candle plot
and record of the most recent trades. The GUI currently supports 
visualization of moving average and MACD indicators, as well as a very 
experimental implementation of a live trade bot based on a moving average 
crossover strategy. I AM IN THE EARLY STAGES OF TESTING THE TRADE BOT;
I DO NOT RECOMMEND USING IT AT THIS TIME UNLESS WITH NEGLIGIBLE AMOUNTS 
OF MONEY. 

On the first run with no local data available, the most recent 2 hours
of trades will be obtained from the API. If set to record data (the default
case), local files of trade and candle data will be accumulated as the 
program continues to run.




Acknowledgements
-------------

Plot design is based on a tutorial series from Sentdex.com

<http://sentdex.com/sentiment-analysisbig-data-and-python-tutorials-algorithmic-trading/how-to-chart-stocks-and-forex-doing-your-own-financial-charting/>

Bitfinex API python implementation is based on sample code by Raphael Nicolle 

<https://community.bitfinex.com/showwiki.php?title=Sample+API+Code>
