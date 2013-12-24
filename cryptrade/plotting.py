""" Tools for plotting of candle data and analytics """

from __future__ import division

import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# needed for customized candlestick from matplotlib.finance
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from utilities import dt_to_ut, ut_to_dt, load_candlefile, parse_period


def candlestick(ax, quotes, width=0.2, colorup='k', colordown='r', colorshadow=None,
                alpha=1.0):

    """
    Modified from matplotlib.finance module. 
    
    quotes is a sequence of (time, open, close, high, low, ...) sequences.
    As long as the first 5 elements are these values,
    the record can be as long as you want (eg it may store volume).

    time must be in float days format - see date2num

    Plot the time, open, close, high, low as a vertical line ranging
    from low to high.  Use a rectangular bar to represent the
    open-close span.  If close >= open, use colorup to color the bar,
    otherwise use colordown

    ax          : an Axes instance to plot to
    width       : fraction of a day for the rectangle width
    colorup     : the color of the rectangle where close >= open
    colordown   : the color of the rectangle where close <  open
    alpha       : the rectangle alpha level

    return value is lines, patches where lines is a list of lines
    added and patches is a list of the rectangle patches added

    """

    OFFSET = width/2.0

    lines = []
    patches = []
    for q in quotes:
        t, open, close, high, low = q[:5]

        if close>=open :
            color = colorup
            lower = open
            height = close-open
        else           :
            color = colordown
            lower = close
            height = open-close
	
	if not colorshadow: colorsh = color
	else: colorsh = colorshadow
        vline = Line2D(
            xdata=(t, t), ydata=(low, high),
            color=colorsh,
            linewidth=1,
            antialiased=True,
            alpha=0.5)

        rect = Rectangle(
            xy    = (t-OFFSET, lower),
            width = width,
            height = height,
            facecolor = color,
            edgecolor = color,
            )
        rect.set_alpha(alpha)


        lines.append(vline)
        patches.append(rect)
        ax.add_line(vline)
        ax.add_patch(rect)
    ax.autoscale_view()

    return lines, patches


class Candleplot(object):
    """ Plotting framework for candle data. Interactive plot allows for 
    updating, otherwise the plot is static and blocks further execution. """
    
    def __init__(self, interactive=False):
        if interactive:
            plt.ion()
        else:
            plt.ioff()
        self.fig = None


    def plot_candlefile(self, candlefile, start=None, end=None, indicators=[]):
        """ Plot a candle graph directly from a candle data file. """
        candles, period = load_candlefile(candlefile)
        
        for indicator in indicators:
            indicator.calculate(candles)
        
        if start:
            candles = [row for row in candles if row[0] >= int(dt_to_ut(start))]
            for indicator in indicators:
                indicator.values = indicator.values[-len(candles):]
        if end:
            candles = [row for row in candles if row[0] < int(dt_to_ut(end))]
            for indicator in indicators:
                indicator.values = indicator.values[:len(candles)]
    
        self.indicators = indicators
        self.plot_candledata(candles, period, indicators)


    def build_plot(self):
        """ Builds the basic plot layout, only called once. """        
        
        ### main frame
        matplotlib.rcParams.update({'font.size': 9})
        self.fig = plt.figure(facecolor='#07000d', figsize=(12,8))
        plt.pause(0.001)
        
        # upper plot
        self.ax1 = ax1 = plt.subplot2grid((5,4), (0,0), rowspan=4, colspan=4, axisbg='#07000d')  # 5high x 4wide grid, ax1 starts at (0,0) and covers 4x3 area  
    
        # lower plot
        self.ax2 = ax2 = plt.subplot2grid((5,4), (4,0), rowspan=1, colspan=4, sharex=ax1, axisbg='#07000d') #sharex causes common x axis and scaling between subplots
        
        # formatting
        ax1.grid(True, color='white', alpha=0.5)
        ax1.spines['bottom'].set_color('#5998ff')
        ax1.spines['top'].set_color('#5998ff')
        ax1.spines['left'].set_color('#5998ff')
        ax1.spines['right'].set_color('#5998ff')
        ax1.tick_params(axis='y', colors='white')
        ax1.yaxis.label.set_color('white')    
    
        ax2.grid(True, color='white', alpha=0.5)
    
        ax2.yaxis.label.set_color('white')
    
        ax2.spines['bottom'].set_color('#5998ff')
        ax2.spines['top'].set_color('#5998ff')
        ax2.spines['left'].set_color('#5998ff')
        ax2.spines['right'].set_color('#5998ff')
        ax2.tick_params(axis='x', colors='white')
        ax2.tick_params(axis='y', colors='white')

    
        plt.subplots_adjust(left=0.06, right=0.97, bottom=0.05, top=0.94, hspace=0)
        plt.pause(0.001)
    
        plt.setp(ax1.get_xticklabels(), visible=False) # hide x labels of upper subplot
        plt.pause(0.001)    
        
        ax2.autoscale_view('tight')

    def candlewidth(self):
        """ Modulates candle width based on candle period. """
        if self.p_unit == 'h':
            w = self.p_value / 24.
        if self.p_unit == 'm':
            w = self.p_value / (24.*60)
        if self.p_unit == 's':
            w = self.p_value / (24.*60*60)
        return w * .75
            

    def plot_candledata(self, candles, period, indicators=[]):
        """ Plot or update a candle graph from candle data. """

        self.p_value, self.p_unit = parse_period(period)
        self.period = period
        
        self.indicators = indicators
        
        if not self.fig:
            self.build_plot()
    
        starts, opens, closes, highs, lows, volumes = np.array(candles).transpose()
        
        dates = [mdates.date2num(ut_to_dt(start)) for start in starts]
        
        candles = np.array([dates, opens, closes, highs, lows, volumes]).transpose()
    
        self.ax1.cla()
        self.ax1.xaxis_date()
    
        # candles
        candlestick(self.ax1, candles, width=self.candlewidth(), colorup='cyan', colordown='blue')

        self.ax1.set_ylabel('USD/BTC')
        self.ax1.autoscale_view('tight')
        self.ax1.grid(True, color='white', alpha=0.5)

        self.ax2.cla()
        self.ax2.xaxis_date()
        
        self.ax2.yaxis.set_ticklabels([]) # hide volume numbers
        
#        ax1.xaxis.set_major_locator(mticker.MaxNLocator(10))   # need to move these after cla()
#        ax2.yaxis.set_major_locator(mticker.MaxNLocator(1))
#        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))        
        
#        for label in ax2.xaxis.get_ticklabels():
#            label.set_rotation(45)
        plt.pause(0.001)
        # indicators
        plot_volume = True # default case
        for indicator in indicators:
            values = indicator.values[-len(dates):]
            if indicator.plot_type == 'primary':
                self.ax1.plot(dates, values, label = indicator.name)
            if indicator.plot_type == 'secondary':
                self.ax2.plot(dates, values, '#00ffe8', linewidth=0.8, label=indicator.name)
                self.ax2.fill_between(dates, 0, [float(x) for x in values], facecolor='#00ffe8', alpha=0.5)
                self.ax2.set_ylabel(indicator.name) 
                plot_volume = False
    
        if plot_volume: 
            bar = False
            if bar:
                self.ax2.bar(dates, volumes, width = self.candlewidth(), facecolor='#00ffe8')    # bar
            else:
                self.ax2.plot(dates, volumes, '#00ffe8', linewidth=0.8)                          # curve
                self.ax2.fill_between(dates, 0, [float(x) for x in volumes], facecolor='#00ffe8', alpha=0.5)
            plt.ylabel('Volume')
            plt.pause(0.001)
    
        ### legend, grid, formatting
        if indicators:
            self.ax1.legend(loc=2, fancybox=True, prop={'size':9})
    
        if plt.isinteractive():
            plt.pause(0.001)
        else:
            plt.show()