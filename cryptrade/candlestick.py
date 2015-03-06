from __future__ import division
# needed for customized candlestick from matplotlib.finance
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


def candlestick(ax, quotes, width=0.2, colorup='k', colordown='r',
                alpha=1.0, colorline=None):

    """
    Modified from matplotlib.finance module to change color of high-low lines.

    quotes is a sequence of (time, open, close, high, low, ...) sequences.
        As long as the first 5 elements are these values,
        the record can be as long as you want (eg it may store volume).

        time must be in float days format - see date2num

        Plots the time, open, close, high, low as a vertical line ranging
        from low to high.  Uses a rectangular bar to represent the
        open-close span.  If close >= open, uses colorup to color the bar,
        otherwise uses colordown.

    ax          : an Axes instance to plot to
    width       : fraction of a day for the rectangle width
    colorup     : the color of the rectangle where close >= open
    colordown   : the color of the rectangle where close <  open
    alpha       : the rectangle alpha level
    colorline   : the color of the high-low line; defaults to colorup/colordown

    return value is lines, patches where lines is a list of lines
    added and patches is a list of the rectangle patches added

    """

    OFFSET = width/2.0

    lines = []
    patches = []
    for q in quotes:
        t, opn, close, high, low = q[:5]

        if close >= opn:
            color = colorup
            lower = opn
            height = close-opn
        else:
            color = colordown
            lower = close
            height = opn-close

        if colorline:
            cl = colorline
        else:
            cl = color

        vline = Line2D(
            xdata=(t, t), ydata=(low, high),
            color=cl,
            linewidth=1,
            antialiased=True,
            alpha=alpha)

        rect = Rectangle(
            xy=(t-OFFSET, lower),
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
