
class ProfiilePlotConverter():
    """Convert profile x(d) value to plot x value and vice versa"""

    def __init__(self):
        self.pLines = []
        self.n_pLine = 0
        self.base_pIndex = 0

        self.norm_factors = []
        self.divs = []
        self.divs_norm = []
        self.dps = 'distance_pixel_sized'

    def set_pLines(self, pLines, base_pLine_index=0):
        """ Set profile lines

            Normalized factors, divs and divs_norm are calculated
        """
        self.pLines = pLines
        self.base_pIndex = base_pLine_index
        self.n_pLine = len(self.pLines)
        self.norm_factors = self.get_norm_factors()
        self.divs = []
        self.divs_norm = []
        for i in range(self.n_pLine):
            self.divs.append(self.get_divs(self.pLines[i]))
            self.divs_norm.append(self.get_divs(self.pLines[i], self.norm_factors[i]))

        return True

    def get_norm_factors(self):
        """ Return normalized factors """
        base_p = self.pLines[self.base_pIndex]
        n_seg = len(base_p)

        out = []
        for pIndex in range(self.n_pLine):
            pLpI = self.pLines[pIndex]
            out.append([1.0 * base_p[seg_index][self.dps] / pLpI[seg_index][self.dps]
                        for seg_index in range(n_seg)])
        return out

    def get_segment(self, x, seg_divs):
        """ Return segment number for x """
        o = 0
        divs_rev = seg_divs[:-1][::-1]
        n = len(divs_rev)
        for i, seg in enumerate(divs_rev):
            if x > seg:
                o = n - i
                break
        return o

    def get_divs(self, pLine, norm_factors=None):
        """ Return list of (normalized) distance of
            each segment end-point from the origin
        """
        seg_d = 0
        seg_divs = []
        n_seg = len(pLine)
        if norm_factors is None:
            norm_factors = [1] * n_seg
        for seg_index in range(n_seg):
            seg_d += pLine[seg_index][self.dps] * norm_factors[seg_index]
            seg_divs.append(seg_d)
        return seg_divs

    def profileX_to_plotX(self, x, pLine_index):
        """ Return x position (distance from the origin) from plot x position """
        divs = self.divs[pLine_index]
        divs_norm = self.divs_norm[pLine_index]
        norm_factors = self.norm_factors[pLine_index]
        seg = self.get_segment(x, divs)

        # insert 0 to the beging for index 0 values
        divs = [0, *divs]
        divs_norm = [0, *divs_norm]

        return (x - divs[seg]) * norm_factors[seg] + divs_norm[seg]

    def plotX_to_profileX(self, x, pLine_index):
        """ Return x position (distance from the origin) from plot x position """
        divs = self.divs[pLine_index]
        divs_norm = self.divs_norm[pLine_index]
        norm_factors = self.norm_factors[pLine_index]
        seg = self.get_segment(x, divs_norm)

        # insert 0 to the beging for index 0 values
        divs = [0, *divs]
        divs_norm = [0, *divs_norm]

        return int((x - divs_norm[seg]) / norm_factors[seg] + divs[seg])


if __name__ == "__main__":
    pLines = [
        [
            {"start": [], "end": [], 'distance': 0, 'distance_pixel_sized': 200},
            {"start": [], "end": [], 'distance': 0, 'distance_pixel_sized': 100},
            {"start": [], "end": [], 'distance': 0, 'distance_pixel_sized': 50},
        ],
        [
            {"start": [], "end": [], 'distance': 0, 'distance_pixel_sized': 100},
            {"start": [], "end": [], 'distance': 0, 'distance_pixel_sized': 200},
            {"start": [], "end": [], 'distance': 0, 'distance_pixel_sized': 20},
        ],
    ]

    data = [
        [[20, 50, 100, 150, 230, 290, 320, 340], [1, 1, 1, 1, 1, 1, 1, 1]],
        [[30, 100, 240, 260, 310], [1, 1, 1, 1, 1]],
    ]

    data_norm = [
        [[20, 50, 100, 150, 230, 290, 320, 340], [1, 1, 1, 1, 1, 1, 1, 1]],
        [[60, 200, 270, 280, 325], [1, 1, 1, 1, 1]],
    ]

    p = ProfiilePlotConverter()

    p.set_pLines(pLines, 0)

    out = []
    print('profile -> plot')
    for x in data[1][0]:
        y = p.profileX_to_plotX(x, 1)
        out.append(y)
    print(data[1][0], out)

    out = []
    print('plot -> profile')
    for x in data_norm[1][0]:
        y = p.plotX_to_profileX(x, 1)
        out.append(y)
    print(data_norm[1][0], out)
