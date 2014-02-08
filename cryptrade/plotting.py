""" Tools for plotting of candle data and analytics """

from __future__ import division

import numpy as np

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.artist import setp
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates

from candlestick import candlestick
from utilities import parse_period, pdelta, ut_to_dt#, trades_to_candles
        

        


class CandlePlot(Figure):
    
    def __init__(self, parent=None):
        self.theme = {'facecolor':'#07000d', 'axisbg':'#07000d', 
                      'spines':'#5998ff', 'grid':'white', 'ticks':'white',
                      'labels':'white'}
                      
        matplotlib.rcParams.update({'font.size': 9})     
        
        super(CandlePlot, self).__init__(figsize=(12,8), facecolor=self.theme['facecolor']) 
        
        self.canvas = FigureCanvas(self)
        self.canvas.setParent(parent)
        
        gs = gridspec.GridSpec(4, 5)
        self.ax1 = self.add_subplot(gs[ :3, : ], axisbg=self.theme['axisbg'])
        self.ax2 = self.add_subplot(gs[ -1, : ], sharex=self.ax1, axisbg=self.theme['axisbg'])

        self.subplots_adjust(left=0.06, right=0.97, bottom=0.05, top=0.94, hspace=0)        
        
        self.formatting()
    
    def formatting(self):
        ax1, ax2 = self.ax1, self.ax2
        ax1.grid(True, color=self.theme['grid'], alpha=0.5)
        ax2.grid(True, color=self.theme['grid'], alpha=0.5)
        
        for region in ['bottom', 'top', 'left', 'right']:
            ax1.spines[region].set_color(self.theme['spines'])
            ax2.spines[region].set_color(self.theme['spines'])
        
        ax1.tick_params(axis='x', colors=self.theme['ticks'])
        ax2.tick_params(axis='x', colors=self.theme['ticks'])
        ax1.tick_params(axis='y', colors=self.theme['ticks'])
        ax2.tick_params(axis='y', colors=self.theme['ticks'])        
        
        ax1.xaxis.label.set_color(self.theme['labels'])
        ax2.xaxis.label.set_color(self.theme['labels'])
        ax1.yaxis.label.set_color(self.theme['labels'])
        ax2.yaxis.label.set_color(self.theme['labels'])
        
        ax1.set_ylabel('USD/BTC')
        
        setp(ax1.get_xticklabels(), visible=False) # hide x labels of upper subplot
        
    def plot(self, candles, period, ncandles=100, indicators=[]):
        
        self.p_value, self.p_unit = parse_period(period)
        
        self.candles = candles
        starts, opens, closes, highs, lows, volumes = np.array(self.candles).transpose()
        dates = [mdates.date2num(ut_to_dt(start)) for start in starts]        
        self.candles = np.array([dates, opens, closes, highs, lows, volumes]).transpose()
    
        start = ut_to_dt(starts[-ncandles]) - pdelta(self.p_value, self.p_unit)
        end = ut_to_dt(starts[-1]) + pdelta(self.p_value, self.p_unit)
    
        self.ax1.cla()
        self.ax1.xaxis_date()
    
        candlestick(self.ax1, self.candles[-ncandles:], width=self.candleWidth(), colorup='cyan', colordown='blue')

        self.ax1.set_xlim(mdates.date2num(start), mdates.date2num(end))

        self.ax2.cla()
        self.ax2.xaxis_date()
        self.ax2.yaxis.set_ticklabels([]) # hide volume numbers

        self.ax2.set_xlim(mdates.date2num(start), mdates.date2num(end))
        
        # indicators
        plot_volume = True # default case
        for indicator in indicators:
            values = indicator.calculate(self.candles)[-ncandles:]
            if indicator.plot_type == 'primary':
                self.ax1.plot(dates[-ncandles:], values[-ncandles:], label = indicator.label)
            if indicator.plot_type == 'secondary':
                self.ax2.plot(dates[-ncandles:], values[-ncandles:], '#00ffe8', linewidth=0.8, label=indicator.label)
                self.ax2.fill_between(dates[-ncandles:], 0, [float(x) for x in values], facecolor='#00ffe8', alpha=0.5)
                self.ax2.set_ylabel(indicator.label) 
                plot_volume = False
    
        if plot_volume: 
            bar = False
            if bar:
                self.ax2.bar(dates[-ncandles:], volumes[-ncandles:], width = self.candlewidth(), facecolor='#00ffe8')    # bar
            else:
                self.ax2.plot(dates[-ncandles:], volumes[-ncandles:], '#00ffe8', linewidth=0.8)                          # curve
                self.ax2.fill_between(dates[-ncandles:], 0, [float(x) for x in volumes[-ncandles:]], facecolor='#00ffe8', alpha=0.5)
            self.ax2.set_ylabel('Volume')
    
        # legend
        if indicators:
            self.ax1.legend(loc=2, fancybox=True, prop={'size':9})

        self.formatting()        
        
        self.canvas.draw() # update                
        
    def candleWidth(self):
        """ Modulates candle width based on candle period. """
        if self.p_unit == 'h':
            w = self.p_value / 24.
        if self.p_unit == 'm':
            w = self.p_value / (24.*60)
        if self.p_unit == 's':
            w = self.p_value / (24.*60*60)
        return w * .75