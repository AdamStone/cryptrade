cryptrade
=========

Cryptrade aims to provide a scalable, modular python framework for cryptocurrency 
trading, including collection and plotting of trade data, backtesting, live 
trading simulation, and live trade botting. 

The current (pre)release includes very limited implementation:

    Moving average crossover strategies    
    Live monitoring and trading simulation of Bitfinex and Bitstamp markets
    Candleplots of live and historical data

Currently only the Bitfinex API is supported, which includes both Bitfinex and 
Bitstamp trade data. Backtesting and live trade botting are in progress.


Dependencies
-------------

NumPy and MatPlotLib libraries are required. 


Getting Started
-------------

A setup.py installer is not yet implemented; scripts can be run from 
the same directory as the cryptrade package, or the cryptrade package can be
placed in the python path. Several example scripts are provided which illustrate 
the basic use. A data directory will be created wherever the scripts are run. 


Issues with Windows
-------------

MatPlotLib interactive mode is not well-behaved on Windows, and plot 
window may resist moving or resizing while showing a (Not Responding) status.
Although annoying, this does not mean the program has crashed; scripts will 
continue to run and the plot will continue to update. This behavior is not 
observed on Linux, and workarounds for Windows are under investigation.

Note that plotting can be disabled for CandleStream and Trader objects by 
setting the optional argument plot_ncandles=0. 


Acknowledgements
-------------

Plot design is based on a tutorial series from Sentdex.com

<http://sentdex.com/sentiment-analysisbig-data-and-python-tutorials-algorithmic-trading/how-to-chart-stocks-and-forex-doing-your-own-financial-charting/>

Bitfinex API python implementation is based on sample code by Raphael Nicolle 

<https://community.bitfinex.com/showwiki.php?title=Sample+API+Code>
