import os
import tempfile
import unittest

from lumen_panel import config


def write(d, name, text):
    path = os.path.join(d, name)
    with open(path, "w") as f:
        f.write(text)
    return path


class ConfigTests(unittest.TestCase):
    def test_defaults_when_no_files(self):
        cfg = config.load(["/nonexistent/panel.toml"])
        self.assertEqual(cfg["panel"]["position"], "top")
        self.assertIn("clock", cfg["layout"]["right"])
        self.assertEqual(cfg["layout"]["left"], ["launcher", "workspaces", "tasks"])

    def test_later_file_overrides_and_tables_merge(self):
        with tempfile.TemporaryDirectory() as d:
            a = write(d, "a.toml", '[panel]\nheight = 40\n[clock]\nformat = "%H:%M"\n')
            b = write(d, "b.toml", "[panel]\nposition = \"bottom\"\n")
            cfg = config.load([a, b])
            self.assertEqual(cfg["panel"]["height"], 40)  # from a
            self.assertEqual(cfg["panel"]["position"], "bottom")  # from b
            self.assertEqual(cfg["panel"]["layer"], "top")  # default survives
            self.assertEqual(cfg["clock"]["format"], "%H:%M")

    def test_layout_list_replaced_not_merged(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "p.toml", '[layout]\nright = ["clock"]\n')
            cfg = config.load([p])
            self.assertEqual(cfg["layout"]["right"], ["clock"])
            self.assertEqual(cfg["layout"]["left"], config.DEFAULTS["layout"]["left"])

    def test_invalid_values_fall_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "p.toml", '[panel]\nposition = "left"\nheight = 9999\n')
            cfg = config.load([p])
            self.assertEqual(cfg["panel"]["position"], "top")
            self.assertEqual(cfg["panel"]["height"], 36)

    def test_broken_toml_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "p.toml", "this is = = not toml")
            cfg = config.load([p])
            self.assertEqual(cfg["panel"]["height"], 36)

    def test_defaults_not_mutated(self):
        before = config.DEFAULTS["panel"]["height"]
        with tempfile.TemporaryDirectory() as d:
            config.load([write(d, "p.toml", "[panel]\nheight = 50\n")])
        self.assertEqual(config.DEFAULTS["panel"]["height"], before)


if __name__ == "__main__":
    unittest.main()
