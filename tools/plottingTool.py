from functools import reduce

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.colors import ColorConverter
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import mpl_toolkits.axisartist as AA
import numpy as np


class PlottingTool:

    def __init__(self, model, tracker):
        self.fig = None
        self.host = None
        self.par = []
        self.plotWidget = None
        self.model = model
        self.mcv = None
        self.cid = None
        self.tracker = tracker

    def getPlotWidget(self):
        bgColor = u'#F9F9F9'
        bgColor = u'#E4E4E4'
        spp = mpl.figure.SubplotParams(left=0, bottom=0,
                                       right=1, top=1,
                                       wspace=0, hspace=0)
        self.fig = Figure(figsize=(1, 1),
                          tight_layout=True,
                          linewidth=0.0, subplotpars=spp)
        self.fig.patch.set_facecolor(bgColor)
        self.mcv = FigureCanvas(self.fig)
        return self.mcv

    def addPlotWidget(self, plotFrame):
        layout = plotFrame.layout()
        if layout.count() == 0:
            layout.addWidget(self.getPlotWidget())
        self.plotWidget = layout.itemAt(0).widget()

    # def formatAxes(self, axe1, axe2=None, axe1_colors=u'k', axe2_colors=u'k'):
    #     # add grrid to the plot
    #     axe1.grid()
    #     # major ticks for left axis with color
    #     axe1.tick_params(axis="y", which="major", colors=axe1_colors,
    #                      direction="in", length=10, width=1, bottom=True,
    #                      top=False, left=True, right=False)
    #     # minor ticks for left axis with color
    #     axe1.minorticks_on()
    #     axe1.tick_params(axis="y", which="minor", colors=axe1_colors,
    #                      direction="in", length=5, width=1, bottom=True,
    #                      top=False, left=True, right=False)

    #     # for X axis
    #     # major tick
    #     axe1.tick_params(axis="x", which="major", colors=u'k',
    #                      direction="in", length=10, width=1, bottom=True,
    #                      top=False, left=True, right=False)
    #     # minor tick
    #     axe1.tick_params(axis="x", which="minor", colors=u'k',
    #                      direction="in", length=5, width=1, bottom=True,
    #                      top=False, left=True, right=False)

    #     if axe2 is not None:
    #         axe2.tick_params(axis="y", which="major", colors=axe2_colors,
    #                          direction="in", length=10, width=1, bottom=False,
    #                          top=False, left=False, right=True)
    #         axe2.minorticks_on()
    #         axe2.tick_params(axis="y", which="minor", colors=axe2_colors,
    #                          direction="in", length=5, width=1, bottom=False,
    #                          top=False, left=False, right=True)

    def getMarkerSize(self, defaultSize, dataLength):
        maxSize = 30
        if dataLength:
            if int(maxSize / dataLength) < defaultSize:
                return int(maxSize / dataLength)
            else:
                return defaultSize
        else:
            return defaultSize

    # def resetPlot(self):
    #     if self.ax is not None:
    #         self.ax.cla()
    #     if self.ax2 is not None:
    #         self.ax2.cla()
    #     self.formatAxes(self.ax, self.ax2)
    #     self.plotWidget.draw()

    def calculateMovingAverage(self, data, N=10):
        offset = 0 if N % 2.0 else 1
        n2 = int(N / 2.0)
        maY = np.convolve(data[1], np.ones((N,)) / N, mode='valid')
        maX = data[0][n2:len(data[0]) - n2 + offset]
        return (maX, maY)

    def movingAverage(self, host, data, color, N=10, linestyle='-'):
        maX, maY = self.calculateMovingAverage(data, N)
        movAve, = host.plot(maX, maY, color=color, linestyle=linestyle)

    def sum_profile_line(self, profile_line):
        return reduce(lambda x, y: x + y['distance_pixel_sized'], profile_line, 0.0)

    def drawPlot3(self, pLines, data, **opt):
        # clear current plot
        self.resetPlot()
        self.par = []

        AxisPadding = 0.1

        dataN = 0
        linestyles = ['-', ':', '--', ':']
        linewidth = [1, 1.5, 1.8, 2]
        symbolAlpha = [1, 0.6, 0.3]

        pLineNorm = opt['pLineNormalized']
        pLineNorm_by_segment = opt['pLineNormalizedBySegment']
        pLineNorm_base_index = 0
        ppc = opt['profilePlotConverter']

        dps = 'distance_pixel_sized'

        """ calculate normalization factors """
        normFactor = []
        if pLineNorm and pLineNorm_by_segment:
            for pIndex in range(len(pLines)):
                """ scan profile line """

                """ normFactor[
                  ['norm factor for pLines[0] seg 0', 'norm factor for pLines[0] seg 1', ...],
                  ['norm factor for pLines[1] seg 0', 'norm factor for pLines[1] seg 1', ...],
                  [...]
                ]

                """

                """ scan segment """
                normFactorBySegment = []
                for i, seg in enumerate(pLines[pLineNorm_base_index]):
                    normFactorBySegment.append(
                        seg[dps] / pLines[pIndex][i][dps])
                normFactor.append(normFactorBySegment)

        elif pLineNorm:
            # normFactor['norm factor for pLines[0]', 'norm factor for pLines[1]', ...]
            deno = self.sum_profile_line(pLines[pLineNorm_base_index])
            [normFactor.append(deno / self.sum_profile_line(pLines[pIndex]))
             for pIndex in range(len(pLines))]
        else:
            # [1, 1, 1, ...] No normalization => all factors are 1
            [normFactor.append(1) for pIndex in range(len(pLines))]

        # find index of longest profile line
        longestN = 0
        longestIndex = 0
        for d in range(len(data)):
            if longestN < len(data[d]):
                longestN = len(data[d])
                longestIndex = d

        hostPlotFlag = True
        myPlot = []
        for d in data[longestIndex]:
            dataN += 1
            if hostPlotFlag:
                myAx = self.host
            else:
                self.par.append(self.host.twinx())
                # self.par.append(ParasiteAxes(self.host, sharex=self.host))
                j = len(self.par) - 1
                # parasite axes
                if j > 0:
                    offset = 50 * j
                    new_fixed_axis = self.par[j].get_grid_helper(
                    ).new_fixed_axis
                    self.par[j].axis["right"] = new_fixed_axis(loc="right",
                                                               axes=self.par[j],
                                                               offset=(offset, 0))
                self.par[j].axis["right"].toggle(all=True)
                myAx = self.par[j]

            tmpPlot = []
            for pIndex in range(len(data)):  # loop for multiple profile lines
                if not len(data[pIndex]):
                    continue
                dd = data[pIndex][dataN - 1]

                """
                dd = {
                    'data': [[x0, x1, x2, ...], [y0, y1, y2, ...]],
                    'label': 'element name',
                    'configs': {
                        'areaSampling': 0,
                        'areaSamplingWidth': 5,
                        ....
                    },
                    'layer': QgsMapLayer,
                    'layer_type': QgsMapLayerType,
                    'color_org': '#xxxxxx'
                }
                """

                """ normalization """
                # normalizing data (x values) by base profile line
                # (default - currently fixed: Profile Line 1)
                if pLineNorm:
                    tmp = []
                    if pLineNorm_by_segment:
                        # apply segmment specific normilization factor to x values
                        tmp = [ppc.profileX_to_plotX(x, pIndex) for x in dd['data'][0]]
                    else:
                        # apply normalizatin factor of each profile line
                        tmp = [x * normFactor[pIndex] for x in dd['data'][0]]

                    dd['data'][0] = tmp

                """ moving average """
                if d['layer_type'] and d['configs']['movingAverage']:
                    self.movingAverage(myAx, dd['data'], dd['color_org'],
                                       dd['configs']['movingAverageN'],
                                       linestyles[pIndex])

                alpha = 0.1 if d['layer_type'] and d['configs']['movingAverage'] else symbolAlpha[pIndex]
                color = ColorConverter().to_rgba(d['color_org'], alpha=alpha)
                marker = d['configs']['plotOptions']['symbol']
                marker_size = d['configs']['plotOptions']['symbolSize']
                line_type = d['configs']['plotOptions']['lineType']
                line_width = d['configs']['plotOptions']['lineWidth']
                my_tmp_Plot, = myAx.plot(dd['data'][0], dd['data'][1],
                                         label=dd['label'], color=color,
                                         linestyle=linestyles[pIndex],
                                         linewidth=line_width,
                                         marker=marker,
                                         # markersize=self.getMarkerSize(10, len(dd['data'][0])))
                                         markersize=marker_size)
                tmpPlot.append(my_tmp_Plot)

            myPlot.append(tmpPlot)
            #
            # Axes styling
            #

            # common setting
            if 'label' in d['configs']['plotOptions'] and d['configs']['plotOptions']['label'] != "":
                plot_label = d['configs']['plotOptions']['label']
            else:
                plot_label = d['label']
            myAx.set_ylabel(plot_label)
            myAx.minorticks_on()

            if hostPlotFlag:
                # X axis
                myAx.set_xlabel(u"Distance [µm]")
                myAx.axis["bottom"].label.set_fontsize(10)
                myAx.axis["bottom"].major_ticklabels.set_fontsize(8)

                # host Y axis (left side)
                myAx.axis["left"].major_ticklabels.set_fontsize(8)
                myAx.axis["left"].label.set_color(d['color_org'])

                # add event listener for marker
                self.cid = self.mcv.mpl_connect(
                    'motion_notify_event', lambda event: self.tracker(event, normFactor))
            else:  # parasite axis (right side)
                myAx.axis["right"].major_ticklabels.set_fontsize(8)
                myAx.axis["right"].label.set_fontsize(10)
                myAx.axis["right"].label.set_color(d['color_org'])
                # rotate right-labels 180 deg.
                myAx.axis["right"].label.set_axis_direction('left')
                myRange = myAx.axis()
                myMargin = (myRange[3] - myRange[2]) * AxisPadding
                myAx.set_ylim(myRange[2] - myMargin, myRange[3] + myMargin)

            hostPlotFlag = False

            if len(myPlot[0]) > 1:
                myAx.legend(myPlot[0], ['Profile 1', 'Profile 2'], ncol=2, fontsize=7)

        """ handle draw segment separators in the plot """
        # draw vertical line for each vertices of profile line(s)
        plColor = [u'red', u'blue', u'green']
        for pIndex in range(len(pLines)):
            d = 0
            for i in range(len(pLines[pIndex]) - 1):  # avoid last line
                # scan segments
                if pLineNorm and pLineNorm_by_segment:
                    # same as pLineNorm base profile line
                    d += pLines[pLineNorm_base_index][i][dps]
                else:
                    d += pLines[pIndex][i][dps] * normFactor[pIndex]
                self.host.axvline(x=d, c=plColor[pIndex], ls=u':', lw=1, alpha=0.3)

        # set x-axis start with 0, end with endpoint of profile line
        dMax = []

        if pLineNorm_by_segment:
            # Length of base profile line (normalizer)
            dMax = [self.sum_profile_line(pLines[pLineNorm_base_index])]
        else:
            [dMax.append(self.sum_profile_line(pLines[pIndex]) * normFactor[pIndex])
             for pIndex in range(len(pLines))]

        self.host.set_xlim(0, max(dMax))
        myRange = self.host.axis()
        myMargin = (myRange[3] - myRange[2]) * AxisPadding
        self.host.set_ylim(myRange[2] - myMargin, myRange[3] + myMargin)

        self.plotWidget.draw()

    def resetPlot(self, clearAll=False):
        if self.cid:
            self.mcv.mpl_disconnect(self.cid)
        try:
            self.fig.delaxes(self.host)
            self.host.clear()
            [i.cla() for i in self.par]
            if clearAll:
                self.mcv.draw()
        except Exception:
            pass
        self.host = self.fig.add_axes(AA.SubplotHost(self.fig, 111))

    def savePlot(self, fileName):
        self.plotWidget.figure.savefig(str(fileName))
