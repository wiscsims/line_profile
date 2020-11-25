import unittest
import random
from tools.profilePlotConverter import ProfiilePlotConverter

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


class ProfilePlotConverterTest(unittest.TestCase):

    def setUp(self):
        self.base_pLine_index = 0
        self.p = ProfiilePlotConverter()
        self.p.set_pLines(pLines, self.base_pLine_index)

    def test_get_norm_factors(self):
        res = self.p.get_norm_factors()
        self.assertEqual(res, [[1, 1, 1], [2, 0.5, 2.5]])

    def test_get_segment(self):
        divs = [100, 200, 300]
        self.assertEqual(self.p.get_segment(100, divs), 0)
        self.assertEqual(self.p.get_segment(150, divs), 1)
        self.assertEqual(self.p.get_segment(230, divs), 2)

    def test_get_divs(self):
        res = self.p.get_divs(self.p.pLines[1])
        self.assertEqual(res, [100, 300, 320])

    def test_get_divs_normalized(self):
        res = self.p.get_divs(self.p.pLines[1], self.p.norm_factors[1])
        self.assertEqual(res, [200, 300, 350])

    def test_profileX_to_plotX(self):
        res = []
        for x in data[1][0]:
            res.append(self.p.profileX_to_plotX(x, 1))

        self.assertEqual(res, data_norm[1][0])

    def test_plotX_to_profileX(self):
        res = []
        for x in data_norm[1][0]:
            res.append(self.p.plotX_to_profileX(x, 1))

        self.assertEqual(res, data[1][0])

    def test_set_pLines(self):
        """ set new profile lines """
        new_pLines = [
            [{'distance_pixel_sized': 100}, {'distance_pixel_sized': 100}, {'distance_pixel_sized': 100}],
            [{'distance_pixel_sized': 200}, {'distance_pixel_sized': 200}, {'distance_pixel_sized': 200}
             ]]
        self.p.set_pLines(new_pLines, 0)
        res = self.p.norm_factors
        self.assertEqual(res, [[1, 1, 1], [0.5, 0.5, 0.5]])


if __name__ == '__main__':
    unittest.main()
