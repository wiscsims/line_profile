import unittest

from tools.uiLayoutState import peak_control_visibility


class PeakControlVisibilityTest(unittest.TestCase):
    def test_absolute_hides_adaptive_window(self):
        self.assertFalse(peak_control_visibility(0, 0, "standard")["adaptive_window"])

    def test_each_adaptive_mode_shows_window(self):
        for index in (1, 2, 3):
            with self.subTest(index=index):
                self.assertTrue(peak_control_visibility(index, 0, "standard")["adaptive_window"])

    def test_only_selected_ranges_shows_range_editor(self):
        self.assertFalse(peak_control_visibility(0, 0, "standard")["selected_ranges"])
        self.assertTrue(peak_control_visibility(0, 1, "standard")["selected_ranges"])
        self.assertFalse(peak_control_visibility(0, 2, "standard")["selected_ranges"])

    def test_only_cwt_shows_cwt_settings(self):
        self.assertFalse(peak_control_visibility(0, 0, "standard")["cwt_settings"])
        self.assertTrue(peak_control_visibility(0, 0, "cwt")["cwt_settings"])


if __name__ == "__main__":
    unittest.main()
