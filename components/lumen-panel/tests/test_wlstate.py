import struct
import unittest

from lumen_panel.wlstate import (
    DesktopState,
    Toplevel,
    Workspace,
    decode_uint_array,
    desktop_ids,
    ordered_workspaces,
    toplevel_states,
)


class ArrayTests(unittest.TestCase):
    def test_raw_wl_array_bytes(self):
        self.assertEqual(decode_uint_array(struct.pack("=3I", 0, 2, 7)), [0, 2, 7])

    def test_trailing_partial_word_ignored(self):
        self.assertEqual(decode_uint_array(struct.pack("=I", 5) + b"\x01"), [5])

    def test_ints_pass_through(self):
        self.assertEqual(decode_uint_array([1, 3]), [1, 3])

    def test_states_skip_unknown_values(self):
        self.assertEqual(toplevel_states(struct.pack("=3I", 2, 1, 99)), frozenset({"activated", "minimized"}))


class ToplevelTests(unittest.TestCase):
    def test_click_minimises_the_focused_window(self):
        self.assertEqual(Toplevel(1, states=frozenset({"activated"})).click_action(), "minimize")

    def test_click_restores_a_minimised_or_background_window(self):
        self.assertEqual(Toplevel(1, states=frozenset({"minimized"})).click_action(), "activate")
        self.assertEqual(Toplevel(1).click_action(), "activate")
        # minimised windows may still report activated; clicking must bring them back
        both = frozenset({"activated", "minimized"})
        self.assertEqual(Toplevel(1, states=both).click_action(), "activate")

    def test_label_truncates_and_falls_back(self):
        self.assertEqual(Toplevel(1, title="notes.md - Mousepad").label(8), "notes.m…")
        self.assertEqual(Toplevel(1, app_id="foot").label(20), "foot")
        self.assertEqual(Toplevel(1).label(20), "Window")

    def test_desktop_id_candidates(self):
        self.assertEqual(desktop_ids("org.xfce.mousepad"), ["org.xfce.mousepad", "mousepad"])
        self.assertEqual(desktop_ids("Firefox-esr"), ["Firefox-esr", "firefox-esr"])
        self.assertEqual(desktop_ids(""), [])


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.state = DesktopState()
        for key, name, coords, bits in [(3, "Three", (2,), 0), (1, "One", (0,), 0), (2, "Two", (1,), 1), (4, "Hidden", (3,), 4)]:
            self.state.workspaces[key] = Workspace(key, name, coords, bits)

    def test_order_by_coordinates_hides_hidden(self):
        self.assertEqual([w.name for w in ordered_workspaces(self.state.workspaces.values())], ["One", "Two", "Three"])

    def test_order_falls_back_to_creation(self):
        ws = [Workspace(2, "b"), Workspace(1, "a")]
        self.assertEqual([w.name for w in ordered_workspaces(ws)], ["a", "b"])

    def test_active_and_neighbours_wrap(self):
        self.assertEqual(self.state.active_workspace().name, "Two")
        self.assertEqual(self.state.neighbour_workspace(1).name, "Three")
        self.assertEqual(self.state.neighbour_workspace(-1).name, "One")
        self.state.workspaces[3].state, self.state.workspaces[2].state = 1, 0
        self.assertEqual(self.state.neighbour_workspace(1).name, "One")

    def test_no_active_workspace(self):
        for w in self.state.workspaces.values():
            w.state = 0
        self.assertIsNone(self.state.neighbour_workspace(1))

    def test_windows_in_creation_order(self):
        self.state.toplevels = {5: Toplevel(5, "b"), 2: Toplevel(2, "a")}
        self.assertEqual([t.title for t in self.state.windows()], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
