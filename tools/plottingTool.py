from functools import reduce

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.colors import ColorConverter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import mpl_toolkits.axisartist as AA
import numpy as np

from .profileProcessing import processed_data
from .detectionScope import ranges_for_plot


class PlottingTool:

    def __init__(self, model, tracker, feature_click_handler=None):
        self.fig = None
        self.host = None
        self.par = []
        self.plotWidget = None
        self.model = model
        self.mcv = None
        self.motion_cid = None
        self.click_cid = None
        self.tracker = tracker
        self.feature_click_handler = feature_click_handler

    def set_feature_click_handler(self, handler):
        self.feature_click_handler = handler

    def getPlotWidget(self):
        bgColor = u'#F9F9F9'
        # bgColor = u'#E4E4E4'
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

    def sum_profile_line(self, profile_line):
        return reduce(lambda x, y: x + y['distance_pixel_sized'], profile_line, 0.0)

    @staticmethod
    def distance_is_visible(distance, ranges, tolerance=1e-9):
        return any(start - tolerance <= distance <= end + tolerance for start, end in ranges)

    @classmethod
    def mask_visible_values(cls, raw_x, values, ranges):
        if ranges is None:
            return list(values)
        return [
            value if cls.distance_is_visible(distance, ranges) else np.nan
            for distance, value in zip(raw_x, values)
        ]

    def drawPlot3(self, pLines, data, **opt):
        # clear current plot
        self.resetPlot()
        self.par = []

        AxisPadding = 0.1

        dataN = 0
        linestyles = ['-', '--', '-.', ':']
        linewidth = [1, 1.5, 1.8, 2]
        symbolAlpha = [1, 0.6, 0.3]

        pLineNorm = opt['pLineNormalized']
        pLineNorm_by_segment = opt['pLineNormalizedBySegment']
        pLineNorm_base_index = 0
        ppc = opt['profilePlotConverter']
        feature_records = opt.get('featureRecords', [])
        feature_profile_index = opt.get('featureProfileIndex')
        feature_raster_layer_id = opt.get('featureRasterLayerId')
        visible_profile_ranges = opt.get('visibleProfileRanges')
        detection_scope_ranges = opt.get('detectionScopeRanges')
        detection_scope_profile_index = opt.get('detectionScopeProfileIndex')

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

        def profile_x_to_plot_x(distance, profile_index):
            if pLineNorm and pLineNorm_by_segment:
                return ppc.profileX_to_plotX(distance, profile_index)
            return distance * normFactor[profile_index]

        if (
            detection_scope_ranges
            and detection_scope_profile_index is not None
            and 0 <= detection_scope_profile_index < len(pLines)
        ):
            converted_ranges = ranges_for_plot(
                detection_scope_ranges,
                lambda distance: profile_x_to_plot_x(
                    distance, detection_scope_profile_index
                ),
            )
            for start, end in converted_ranges:
                self.host.axvspan(
                    start,
                    end,
                    facecolor="#e6b800",
                    alpha=0.10,
                    edgecolor="none",
                    zorder=0,
                )

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
                profile_data = processed_data(dd)
                raw_x = list(profile_data[0])
                plot_x = list(raw_x)
                if pLineNorm:
                    if pLineNorm_by_segment:
                        # apply segmment specific normilization factor to x values
                        plot_x = [ppc.profileX_to_plotX(x, pIndex) for x in plot_x]
                    else:
                        # apply normalizatin factor of each profile line
                        plot_x = [x * normFactor[pIndex] for x in plot_x]

                profile_ranges = (
                    visible_profile_ranges.get(pIndex, [])
                    if visible_profile_ranges is not None
                    else None
                )

                color = ColorConverter().to_rgba(d['color_org'], alpha=symbolAlpha[pIndex])
                marker = d['configs']['plotOptions']['symbol']
                marker_size = d['configs']['plotOptions']['symbolSize']
                line_type = d['configs']['plotOptions']['lineType']
                line_width = d['configs']['plotOptions']['lineWidth']
                visible_y = self.mask_visible_values(raw_x, profile_data[1], profile_ranges)
                my_tmp_Plot, = myAx.plot(plot_x, visible_y,
                                         label=dd['label'], color=color,
                                         linestyle=linestyles[pIndex],
                                         linewidth=line_width,
                                         marker=marker,
                                         # markersize=self.getMarkerSize(10, len(dd['data'][0])))
                                         markersize=marker_size)
                tmpPlot.append(my_tmp_Plot)

                if (
                    pIndex == feature_profile_index
                    and dd.get('raster_layer_id') == feature_raster_layer_id
                    and feature_records
                ):
                    for kind, marker, color in (
                        ('peak', '^', '#dc2828'),
                        ('valley', 'v', '#285adc'),
                    ):
                        selected = [
                            record
                            for record in feature_records
                            if record['kind'] == kind
                            and (
                                profile_ranges is None
                                or self.distance_is_visible(record['distance'], profile_ranges)
                            )
                        ]
                        if selected:
                            marker_x = []
                            for record in selected:
                                value = record['distance']
                                if pLineNorm:
                                    value = (
                                        ppc.profileX_to_plotX(value, pIndex)
                                        if pLineNorm_by_segment
                                        else value * normFactor[pIndex]
                                    )
                                marker_x.append(value)
                            myAx.scatter(
                                marker_x,
                                [record['value'] for record in selected],
                                marker=marker,
                                color=color,
                                edgecolors='white',
                                linewidths=0.6,
                                s=45,
                                zorder=10,
                                label='_nolegend_',
                            )

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
                # Keep the vertical label inside narrow docked plot canvases.
                myAx.axis["left"].label.set_pad(2)

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
            raw_d = 0
            for i in range(len(pLines[pIndex]) - 1):  # avoid last line
                raw_d += pLines[pIndex][i][dps]
                profile_ranges = (
                    visible_profile_ranges.get(pIndex, [])
                    if visible_profile_ranges is not None
                    else None
                )
                if profile_ranges is None or self.distance_is_visible(raw_d, profile_ranges):
                    self.host.axvline(
                        x=profile_x_to_plot_x(raw_d, pIndex),
                        c=plColor[pIndex],
                        ls=u':',
                        lw=1,
                        alpha=0.3,
                    )

        # set x-axis start with 0, end with endpoint of profile line
        dMax = []

        if visible_profile_ranges is not None:
            visible_plot_limits = [
                profile_x_to_plot_x(distance, pIndex)
                for pIndex, ranges in visible_profile_ranges.items()
                if pIndex < len(pLines)
                for visible_range in ranges
                for distance in visible_range
            ]
            if visible_plot_limits:
                minimum = min(visible_plot_limits)
                maximum = max(visible_plot_limits)
                if minimum == maximum:
                    maximum = minimum + 1.0
                self.host.set_xlim(minimum, maximum)
            else:
                self.host.set_xlim(0, 1)
        elif pLineNorm_by_segment:
            # Length of base profile line (normalizer)
            dMax = [self.sum_profile_line(pLines[pLineNorm_base_index])]
            self.host.set_xlim(0, max(dMax))
        else:
            [dMax.append(self.sum_profile_line(pLines[pIndex]) * normFactor[pIndex])
             for pIndex in range(len(pLines))]
            self.host.set_xlim(0, max(dMax))
        myRange = self.host.axis()
        myMargin = (myRange[3] - myRange[2]) * AxisPadding
        self.host.set_ylim(myRange[2] - myMargin, myRange[3] + myMargin)

        self.motion_cid = self.mcv.mpl_connect(
            'motion_notify_event', lambda event: self.tracker(event, normFactor))
        if self.feature_click_handler is not None:
            self.click_cid = self.mcv.mpl_connect(
                'button_press_event',
                lambda event: self.feature_click_handler(event, normFactor),
            )

        self.plotWidget.draw()

    def resetPlot(self, clearAll=False):
        if self.motion_cid:
            self.mcv.mpl_disconnect(self.motion_cid)
            self.motion_cid = None
        if self.click_cid:
            self.mcv.mpl_disconnect(self.click_cid)
            self.click_cid = None
        if self.host is not None:
            self.fig.delaxes(self.host)
            self.host.clear()
            [i.cla() for i in self.par]
            if clearAll:
                self.mcv.draw()
        self.host = self.fig.add_axes(AA.SubplotHost(self.fig, 111))

    def savePlot(self, fileName):
        self.plotWidget.figure.savefig(str(fileName))
