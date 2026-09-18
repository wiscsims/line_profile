import unittest

from tests.qgis_stubs import install

install()

from tools.profileLineTool import ProfileLineTool


class Marker:
    def __init__(self):
        self.was_reset = False

    def reset(self):
        self.was_reset = True


class Scene:
    def __init__(self):
        self.removed = []

    def removeItem(self, item):
        self.removed.append(item)


def profile(markers=None):
    markers = markers or {}
    return {
        "point": [object()],
        "markers": {
            "line": markers.get("line", Marker()),
            "vertex": markers.get("vertex", []),
            "tieline": markers.get("tieline", []),
            "sampling_area": markers.get("sampling_area", []),
            "sampling_point": markers.get("sampling_point", []),
            "feature_point": markers.get("feature_point", []),
        },
    }


class ProfileLineToolTest(unittest.TestCase):
    def setUp(self):
        self.tool = ProfileLineTool.__new__(ProfileLineTool)
        self.tool.profile_line_index = 1
        self.tool.scene = Scene()
        self.tool.terminated = True
        self.tool.tracking_marker = None
        self.tool.profile_line_points = [[object()]]
        self.tool.profile_lines = [object()]
        self.tool.profile = [profile(), profile()]

    def test_explicit_zero_sampling_index_is_preserved(self):
        self.tool.get_base_sampling_point_vertex_marker = lambda color, point: Marker()
        self.tool.add_sampling_points(0, [[[1, 2]]])
        self.assertEqual(len(self.tool.profile[0]["markers"]["sampling_point"]), 1)
        self.assertEqual(len(self.tool.profile[1]["markers"]["sampling_point"]), 0)

    def test_reset_profile_zero_does_not_clear_profile_one(self):
        zero_marker = Marker()
        one_marker = Marker()
        self.tool.profile[0] = profile({"sampling_point": [zero_marker]})
        self.tool.profile[1] = profile({"sampling_point": [one_marker]})
        self.tool.reset_profile(0)
        self.assertEqual(self.tool.profile[0]["markers"]["sampling_point"], [])
        self.assertEqual(self.tool.profile[1]["markers"]["sampling_point"], [one_marker])
        self.assertIn(zero_marker, self.tool.scene.removed)
        self.assertNotIn(one_marker, self.tool.scene.removed)

    def test_reset_profile_one_does_not_clear_profile_zero(self):
        zero_marker = Marker()
        one_marker = Marker()
        self.tool.profile[0] = profile({"sampling_area": [zero_marker]})
        self.tool.profile[1] = profile({"sampling_area": [one_marker]})
        self.tool.reset_profile(1)
        self.assertEqual(self.tool.profile[1]["markers"]["sampling_area"], [])
        self.assertEqual(self.tool.profile[0]["markers"]["sampling_area"], [zero_marker])
        self.assertIn(one_marker, self.tool.scene.removed)
        self.assertNotIn(zero_marker, self.tool.scene.removed)

    def test_reset_cleanup_does_not_depend_on_reset_return_value(self):
        marker = Marker()
        self.tool.profile[0] = profile({"vertex": [marker]})
        self.tool.reset_profile(0)
        self.assertTrue(marker.was_reset)
        self.assertIn(marker, self.tool.scene.removed)

    def test_remove_all_canvas_items_removes_every_owned_graphic(self):
        tracking = Marker()
        first_markers = {
            "line": Marker(),
            "vertex": [Marker()],
            "tieline": [Marker()],
            "sampling_area": [Marker()],
            "sampling_point": [Marker()],
            "feature_point": [Marker()],
        }
        second_markers = {
            "line": Marker(),
            "vertex": [Marker()],
            "tieline": [Marker()],
            "sampling_area": [Marker()],
            "sampling_point": [Marker()],
            "feature_point": [Marker()],
        }
        self.tool.profile = [profile(first_markers), profile(second_markers)]
        self.tool.tracking_marker = tracking

        expected = [tracking]
        for markers in (first_markers, second_markers):
            expected.append(markers["line"])
            for name in (
                "vertex", "tieline", "sampling_area", "sampling_point", "feature_point"
            ):
                expected.extend(markers[name])

        self.tool.remove_all_canvas_items()

        self.assertCountEqual(self.tool.scene.removed, expected)
        self.assertEqual(self.tool.profile, [])
        self.assertEqual(self.tool.profile_line_points, [])
        self.assertEqual(self.tool.profile_lines, [])
        self.assertIsNone(self.tool.tracking_marker)
        self.assertTrue(self.tool.terminated)


if __name__ == "__main__":
    unittest.main()
