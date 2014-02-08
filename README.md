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


GUI Usage
-------------


![Market view window](/screenshots/marketwindow.png)

Upon starting the GUI, the market view window will display a candle 
graph of recent prices. Individual trades are listed at the bottom.


![Adding indicators](/screenshots/addindicator.png)

The "Add indicators" button opens the indicator dialog where new indicators
can be selected. Simple and exponential moving averages (SMA and EMA) 
and moving average convergence-divergence (MACD) indicators are currently 
implemented. 


![Market view with indicators](/screenshots/withindicators.png)

Plots of indicators can be toggled on and off from the market view window
from the list in the lower-right corner.


![Setting up trading](/screenshots/tradersetup.png)

The "Trader setup" button opens a dialog where a trading strategy is
selected (currently only a Moving Average Crossover strategy is 
implemented). If an API key was not provided when the gui was initialized,
it should be entered here to begin live trading (still in testing and not
recommended!).


![Trader window](/screenshots/traderwindow.png)

The trader window draws from the API to list personal trade history, 
current open orders, and current finances. 


Acknowledgements
-------------

Plot design is based on a tutorial series from Sentdex.com

<http://sentdex.com/sentiment-analysisbig-data-and-python-tutorials-algorithmic-trading/how-to-chart-stocks-and-forex-doing-your-own-financial-charting/>

Bitfinex API python implementation is based on sample code by Raphael Nicolle 

<https://community.bitfinex.com/showwiki.php?title=Sample+API+Code>
