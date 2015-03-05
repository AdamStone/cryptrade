#!/usr/bin/python

""" Start user interface for live candle plot. """

from cryptrade import Gui

# trade and candle data will be saved to a data directory
gui = Gui(record_trades=True, record_candles=True)

# optional; initialize GUI with API key
#gui.setApiKey('your API "key" ', 'your API "secret" ')

gui.run()
