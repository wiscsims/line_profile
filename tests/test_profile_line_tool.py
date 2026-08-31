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
        },
    }


class ProfileLineToolTest(unittest.TestCase):
    def setUp(self):
        self.tool = ProfileLineTool.__new__(ProfileLineTool)
        self.tool.profile_line_index = 1
        self.tool.scene = Scene()
        self.tool.terminated = True
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


if __name__ == "__main__":
    unittest.main()
