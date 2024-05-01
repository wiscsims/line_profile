from functools import reduce

from math import atan, cos, sin, sqrt
from qgis.core import QgsPointXY, QgsRaster, NULL


class DataProcessingTool:
    def __init__(self, n_profile_lines):
        self.tieLine = []
        self.tieLineFlag = False
        self.tieLineDone = []
        self.samplingPoints = []
        self.samplingRange = []
        self.samplingArea = []
        self.samplingWidth = 0

        self.sampling_points = []  # [{profile-1}, {profile-2'}]
        self.sampling_areas = []
        """
        data structure of sampling_points
        each profile line has list of points data with layer_id
        [
            {   # Profile 1
                'layer_id-1': [list_of_QgsPointXY],
                'layer_id-2': [list_of_QgsPointXY],
                ...
            },
            {   # Profile 2
                'layer_id-1': [list_of_QgsPointXY],
                'layer_id-2': [list_of_QgsPointXY],
                ...
            },
        ]
        """
        self.init_area_samplings(n_profile_lines)

        self.pixel_size = 1

    def init_area_samplings(self, n_profile_lines):
        for n in range(n_profile_lines):
            self.sampling_points.append({})
            self.sampling_areas.append({})

    def getProfileLines(self, profilePoints):
        out = []
        for i in range(len(profilePoints) - 1):
            pt1 = profilePoints[i]
            pt2 = profilePoints[i + 1]
            a, b = self.calcSlopeIntercept(pt1, pt2)
            out.append(
                {
                    # [x, y] start
                    "start": pt1,
                    # [x, y] end
                    "end": pt2,
                    "slope": a,  # slope
                    "intercept": b,  # intercept
                    "distance": self.getDistance(pt1, pt2),
                    "distance_pixel_sized": self.getDistance(pt1, pt2) * self.pixel_size,
                }
            )
        return out

    def getVectorProfile(self, pLines, layer, field, distLimit=1e8, distanceField=None, pIndex=0):
        x, y, d = [], [], 0

        if layer.dataProvider().fieldNameIndex(distanceField) == -1:
            distanceField = None

        if layer.selectedFeatureCount() > 0:
            featuresForPlot = layer.selectedFeatures()
        else:
            featuresForPlot = layer.getFeatures()

        if distanceField:
            layer.startEditing()

        lid = layer.id()

        while len(self.tieLine) <= pIndex:
            self.tieLine.append([])
            self.tieLineDone.append([])

        if lid not in self.tieLineDone[pIndex]:
            tieLineFlag = True
            self.tieLineDone[pIndex].append(lid)
        else:
            tieLineFlag = False

        for f in featuresForPlot:
            # calc coordinates of intercept between normal line and profile line
            # if type(f.attribute(field)) is type(QPyNullVariant(int)):
            if f.attribute(field) == NULL:
                continue
            pt = f.geometry().asPoint()
            prjPoint = self.getProjectedPoint(pLines, pt, distLimit)
            if prjPoint is not False:
                d = self.sumD(pLines[: prjPoint[2]])
                d += self.getDistance([prjPoint[0], prjPoint[1]], pLines[prjPoint[2]]["start"])
                x.append(d)
                y.append(f.attribute(field))

                if tieLineFlag:
                    self.addTieLine(pIndex, list(pt), prjPoint[:2])

                if distanceField:
                    f[distanceField] = d
            layer.updateFeature(f)

        if distanceField:
            layer.commitChanges()
        x, y = self.sortDataByX(x, y)

        x = [v * self.pixel_size for v in x]

        return [x, y]

    def sortDataByX(self, x, y):
        sorted_x = list(x)
        sorted_y = []
        sorted_x.sort()
        for i in sorted_x:
            idx = x.index(i)
            sorted_y.append(y[idx])
            x[idx] = None
        return sorted_x, sorted_y

    def sumD(self, pLines):
        return reduce(lambda x, y: x + y["distance_pixel_sized"], pLines, 0.0)

    def getCurrentCoordinates(self, pLines, dist):
        d = 0.0
        for k, v in enumerate(pLines):
            d += v["distance_pixel_sized"]
            if dist < d:
                dist -= d - v["distance_pixel_sized"]
                break
        cu = pLines[k]
        # vertical
        if cu["slope"] == float("inf"):
            dX = 0
            dY = dist / self.pixel_size
        else:
            dX = cos(atan(cu["slope"])) * dist / self.pixel_size
            dY = cu["slope"] * dX
        # +/- direction
        tmp = 1 if cu["end"][1] > cu["start"][1] else -1
        xDirection = 1 if cu["end"][0] > cu["start"][0] else -1
        yDirection = tmp if cu["slope"] >= 0 else tmp * -1
        x = cu["start"][0] + xDirection * dX
        y = cu["start"][1] + yDirection * dY

        return [x, y]

    def getRasterProfile(self, pLines, layer, band, fullRes, raster_layer_id, equiWidth=0, profile_index=None):
        if profile_index is None:
            return

        x = []
        y = []

        self.initSamplingPoints()
        self.initSamplingRange()
        self.initSamplingArea()

        if self.pixel_size == 0:
            return [x, y]

        dp = layer.dataProvider()
        band = int(band.replace("Band ", ""))
        pixelSize = layer.rasterUnitsPerPixelX() if fullRes else 1

        # index number of current segment
        cP = 0

        # current distance from the start point of the profile line
        current_d = 0

        # total distance of profile line
        total_d = self.sumD(pLines)

        # max distance up to the current segment
        current_seg_max_d = self.sumD(pLines[0 : cP + 1])

        current_X, current_Y = pLines[cP]["start"]
        equiWidth = int(round(equiWidth / 2 / (pixelSize * self.pixel_size)))
        self.setSamplingWidth(equiWidth)

        # flag_segment_first_spot = True

        acP = -1

        while current_d < total_d:
            # first point of each segment
            # if current_d >= curent_seg_max_d or current_d == 0:
            if current_d >= current_seg_max_d or current_d == 0:
                # except starting point of profline line
                if current_d > 0:
                    cP += 1

                    # last spot of former segment
                    current_d = current_seg_max_d

                    current_X, current_Y = pLines[cP]["start"]
                    # new max distance up to current segment
                    current_seg_max_d = self.sumD(pLines[0 : cP + 1])

                # set slope and directon of current segment
                slope, direction = self.getDirectionSlope(pLines[cP])

                # calculate step sizes of X, Y and direction
                if slope is False:  # vertical
                    dX = 0
                    dY = 1
                    if pLines[cP]["start"][1] > pLines[cP]["end"][1]:
                        dY *= -1
                else:
                    dX = abs(cos(atan(pLines[cP]["slope"]))) * direction
                    dY = abs(sin(atan(pLines[cP]["slope"]))) * direction * slope

                # scale by pixel size of raster layer
                dX *= pixelSize
                dY *= pixelSize

            # qgsPoint
            # find equilevel
            # get equilevel points => equiPoints

            """ get sampling area rectable """
            if acP != cP:
                acP = cP
                # start point
                acP_s = self.getEquiPoints(pLines[acP]["start"][0], pLines[acP]["start"][1], equiWidth, dX, dY)
                # end point
                acP_e = self.getEquiPoints(pLines[acP]["end"][0], pLines[acP]["end"][1], equiWidth, dX, dY)

                # sampling area (coordinates of the rectangle)
                self.addSamplingArea([acP_s[0], acP_s[-1], acP_e[0], acP_e[-1]])

            """ get points within sampling width """
            equiPoints = self.getEquiPoints(current_X, current_Y, equiWidth, dX, dY)

            tmpVal = 0

            """ sampling points by coordinates [x, y] """
            self.addSamplingRange(equiPoints)
            for n in range(0, len(equiPoints)):
                qgsPoint = QgsPointXY(*equiPoints[n])
                tmpVal += self.getPointValue(dp, qgsPoint, band)

            aveVal = tmpVal / len(equiPoints)

            y.append(aveVal)
            x.append(current_d)

            """ sampling points by QgsPointXY """
            self.samplingPoints.append(QgsPointXY(current_X, current_Y))

            current_X += dX
            current_Y += dY
            current_d += pixelSize

        else:  # while-else
            """ end point """
            # run only one time after exit from while block
            endPoint = pLines[len(pLines) - 1]["end"]
            # qgsPoint = QgsPoint(curernt_X, current_Y)
            equiPoints = self.getEquiPoints(endPoint[0], endPoint[1], equiWidth, dX, dY)
            tmpVal = 0
            self.addSamplingRange(equiPoints)
            for n in range(0, len(equiPoints)):
                qgsPoint = QgsPointXY(*equiPoints[n])
                tmpVal += self.getPointValue(dp, qgsPoint, band)
            aveVal = tmpVal / len(equiPoints)
            y.append(aveVal)
            x.append(total_d)
            self.samplingPoints.append(endPoint)

        # apply pixel size
        x = [v * self.pixel_size for v in x]

        # self.sampling_points[profile_index][layer.id()] = self.samplingPoints

        self.sampling_points[profile_index][raster_layer_id] = self.getSamplingRange()
        self.sampling_areas[profile_index][raster_layer_id] = self.getSamplingArea()

        return [x, y]

    def getEquiPoints(self, x, y, w, dx, dy):
        """Return points within sampling width (w)"""
        out = []
        if w < 1:
            out = [[x, y]]
        else:
            rdx = dy
            rdy = -dx
            for i in range(-w, w + 1):
                out.append([x + i * rdx, y + i * rdy])
        return out

    def getPointValue(self, dp, point, band):
        res = dp.identify(point, QgsRaster.IdentifyFormatValue).results()
        return res[band] if res[band] is not None else 0

    def getProjectedPoint(self, pLines, pt, distLimit):
        minDist = 1.0e12
        tmpDist = 0.0
        x = None  # coordinate x
        y = None  # coordinate y
        i = 0

        for index, pLine in enumerate(pLines):
            slope = pLine["slope"]
            intercept = pLine["intercept"]
            # vertical profile line
            if slope == float("inf"):
                tmpx = pLine["end"][0]
                tmpy = pt[1]
            elif slope == 0:  # horizontal profile line
                tmpx = pt[1]
                tmpy = pLine["end"][1]
            # point on profile line
            elif pt[1] == slope * pt[0] + intercept:
                tmpx = pt[0]
                tmpy = pt[1]
            else:  # others
                a = -1 / slope
                b = pt[1] - (a * pt[0])
                tmpx = (b - intercept) / (slope - a)
                tmpy = a * tmpx + b

            tmpDist = self.getDistance(pt, [tmpx, tmpy])

            # apply pixel size
            tmpDist *= self.pixel_size

            if self.isPointOnProfilefLine(tmpx, tmpy, pLine):
                if minDist > tmpDist:
                    minDist = tmpDist
                    x = tmpx
                    y = tmpy
                    i = index

        # check vertices
        cV = self.getClosestVertex(pLines, pt)

        if x is None and cV["seg"] == -1:
            return False

        if x is None and cV["seg"] > -1:
            # vertex is the projjected point
            i = cV["seg"]
            minDist = cV["distance"]
            x, y = pLines[i]["end"]
        elif x is not None and cV["seg"] > -1:
            if cV["distance"] < minDist:
                # vertex is closer than normal line
                i = cV["seg"]
                x, y = pLines[i]["end"]

        if minDist > distLimit:
            return False

        return [x, y, i]

    def isPointOnProfilefLine(self, x, y, pLine):
        if pLine["start"][0] < pLine["end"][0]:
            lx = pLine["start"][0]
            hx = pLine["end"][0]
        else:
            lx = pLine["end"][0]
            hx = pLine["start"][0]
        if pLine["start"][1] < pLine["end"][1]:
            ly = pLine["start"][1]
            hy = pLine["end"][1]
        else:
            ly = pLine["end"][1]
            hy = pLine["start"][1]
        if lx <= x <= hx and ly <= y <= hy:
            return True
        return False

    def getClosestVertex(self, pLines, pt):
        d = 1.0e12
        segment = 0
        # First and last vertices shouldn't be the closest vertex.
        for index, pLine in enumerate(pLines):
            if index == 0:
                tmpD = self.getDistance(pLine["end"], pt)
                # excluding first vertex
                if self.getDistance(pLine["start"], pt) < tmpD:
                    return {"seg": -1}
            else:
                tmpD = self.getDistance(pLine["end"], pt)
            if d > tmpD:
                d = tmpD
                segment = index
        # excluding last vertex
        if segment == len(pLines) - 1:
            return {"seg": -1}

        return {"seg": segment, "distance": d}

    def calcNormalLine(self, pt, slope, intercept):
        x, y = pt
        if slope == 0 and intercept == 0:
            # profile line is vertical line
            # get horizontal line
            a = 0
            b = y
        elif slope == 0:
            # profile line is horizontal line
            # get vertical line
            a = float("inf")
            b = None
        else:
            a = -1 / slope
            b = y - (a * x)
        return [a, b]

    def calcSlopeIntercept(self, pt1, pt2):
        # a: slope, b: intercept
        if pt1[0] == pt2[0] and pt1[1] == pt2[1]:  # identical
            a = None
            b = None
        elif pt2[1] == pt1[1]:  # horizontal
            a = 0
            b = pt2[1]
        elif pt2[0] == pt1[0]:  # vertical
            a = float("inf")
            b = None
        else:
            a = (pt2[1] - pt1[1]) / (pt2[0] - pt1[0])
            b = pt2[1] - a * pt2[0]
        return [a, b]

    def getDistance(self, pt1, pt2):
        return sqrt((pt2[0] - pt1[0]) ** 2 + (pt2[1] - pt1[1]) ** 2)

    def initTieLines(self):
        self.tieLine = []
        self.tieLineFlag = False
        self.tieLineDone = []

    def addTieLine(self, pIndex, pt1, pt2):
        self.tieLine[pIndex].append([pt1, pt2])

    def getTieLines(self):
        return self.tieLine

    def initSamplingPoints(self):
        self.samplingPoints = []

    def getSamplingPoints(self):
        return self.samplingPoints

    def initSamplingRange(self):
        self.samplingRange = []

    def initSamplingArea(self):
        self.samplingArea = []

    def addSamplingRange(self, point):
        self.samplingRange.append(point)

    def addSamplingArea(self, myList):
        self.samplingArea.append(myList)

    def getSamplingRange(self):
        return self.samplingRange

    def getSamplingArea(self):
        return self.samplingArea

    def setSamplingWidth(self, width):
        self.samplingWidth = width

    def getSamplingWidth(self):
        return self.samplingWidth

    def getDirectionSlope(self, pt):
        start = pt["start"]
        end = pt["end"]

        if end[0] > start[0]:
            direction = 1
            if end[1] > start[1]:
                slope = 1
            elif end[1] < start[1]:
                slope = -1
            else:
                slope = 0
        elif end[0] < start[0]:
            direction = -1
            if end[1] < start[1]:
                slope = 1
            elif end[1] > start[1]:
                slope = -1
            else:
                slope = 0
        else:
            slope = False
            direction = False
        return [slope, direction]
