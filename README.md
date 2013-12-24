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


Getting Started
-------------

A setup.py installer is not yet implemented; scripts can be run from 
the same directory as the cryptrade package, or the cryptrade package can be
placed in the python path. Several example scripts are provided which illustrate 
the basic use. A data directory will be created wherever the scripts are run. 


Acknowledgements
-------------

Plot design is based on a tutorial series from Sentdex.com

<http://sentdex.com/sentiment-analysisbig-data-and-python-tutorials-algorithmic-trading/how-to-chart-stocks-and-forex-doing-your-own-financial-charting/>

Bitfinex API python implementation is based on sample code by Raphael Nicolle 

<https://community.bitfinex.com/showwiki.php?title=Sample+API+Code>
