import unittest

from tests.qgis_stubs import install

install()

from qgis.core import QgsRectangle

from tools.dataProcessingTool import DataProcessingTool
from tools.profileVisibility import profile_visible_ranges, visible_profile_ranges


class ProfileVisibilityTest(unittest.TestCase):
    def setUp(self):
        self.processing = DataProcessingTool(2)
        self.extent = QgsRectangle(0, 0, 10, 10)

    def profile(self, points, pixel_size=1):
        self.processing.pixel_size = pixel_size
        return self.processing.getProfileLines(points)

    def assert_ranges_almost_equal(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for actual_range, expected_range in zip(actual, expected):
            self.assertAlmostEqual(actual_range[0], expected_range[0])
            self.assertAlmostEqual(actual_range[1], expected_range[1])

    def test_one_visible_interval_detects_segment_with_outside_endpoints(self):
        profile = self.profile([[-5, 5], [15, 5]])
        self.assert_ranges_almost_equal(
            profile_visible_ranges(profile, self.extent),
            [(5, 15)],
        )

    def test_no_intersection(self):
        profile = self.profile([[-5, 20], [15, 20]])
        self.assertEqual(profile_visible_ranges(profile, self.extent), [])

    def test_full_intersection(self):
        profile = self.profile([[2, 5], [8, 5]])
        self.assert_ranges_almost_equal(
            profile_visible_ranges(profile, self.extent),
            [(0, 6)],
        )

    def test_multiple_disjoint_intersections_remain_separate(self):
        profile = self.profile(
            [[-10, 5], [5, 5], [5, 15], [8, 15], [8, 5], [20, 5]]
        )
        self.assert_ranges_almost_equal(
            profile_visible_ranges(profile, self.extent),
            [(10, 20), (33, 40)],
        )

    def test_multiple_profiles_are_calculated_independently(self):
        profiles = [
            self.profile([[-5, 5], [15, 5]]),
            self.profile([[5, -10], [5, 20]]),
        ]
        actual = visible_profile_ranges(profiles, self.extent)
        self.assert_ranges_almost_equal(actual[0], [(5, 15)])
        self.assert_ranges_almost_equal(actual[1], [(10, 20)])

    def test_pixel_size_scales_raw_profile_distance(self):
        profile = self.profile([[-5, 5], [15, 5]], pixel_size=2.5)
        self.assert_ranges_almost_equal(
            profile_visible_ranges(profile, self.extent),
            [(12.5, 37.5)],
        )

    def test_line_on_extent_boundary_is_visible(self):
        profile = self.profile([[-5, 0], [15, 0]])
        self.assert_ranges_almost_equal(
            profile_visible_ranges(profile, self.extent),
            [(5, 15)],
        )


if __name__ == "__main__":
    unittest.main()
