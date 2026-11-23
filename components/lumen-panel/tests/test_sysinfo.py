import os
import tempfile
import unittest

from lumen_panel import sysinfo

STAT_A = "cpu  100 0 100 800 0 0 0 0 0 0\ncpu0 50 0 50 400 0 0 0 0 0 0\n"
STAT_B = "cpu  200 0 200 900 0 0 0 0 0 0\ncpu0 100 0 100 450 0 0 0 0 0 0\n"

MEMINFO = """MemTotal:       8000000 kB
MemFree:         500000 kB
MemAvailable:   6000000 kB
Buffers:         100000 kB
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class CpuTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(sysinfo.parse_cpu_times(STAT_A), (800, 1000))

    def test_first_sample_has_no_value(self):
        self.assertIsNone(sysinfo.CpuSampler().update(STAT_A))

    def test_utilisation(self):
        s = sysinfo.CpuSampler()
        s.update(STAT_A)
        # delta: total 300, idle 100 -> 200/300 busy
        self.assertAlmostEqual(s.update(STAT_B), 200 / 3)

    def test_no_progress_is_zero(self):
        s = sysinfo.CpuSampler()
        s.update(STAT_A)
        self.assertEqual(s.update(STAT_A), 0.0)

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            sysinfo.parse_cpu_times("nonsense")


class MemoryTests(unittest.TestCase):
    def test_used_is_total_minus_available(self):
        self.assertEqual(sysinfo.parse_meminfo(MEMINFO), (2000000, 8000000))

    def test_format(self):
        self.assertEqual(sysinfo.format_kib(2 * 1024 * 1024), "2.0 GiB")
        self.assertEqual(sysinfo.format_kib(512 * 1024), "512 MiB")


class BatteryTests(unittest.TestCase):
    def test_missing_root(self):
        self.assertIsNone(sysinfo.read_battery("/nonexistent/path"))

    def test_skips_mains_and_reads_battery(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "AC", "type"), "Mains\n")
            write(os.path.join(d, "BAT0", "type"), "Battery\n")
            write(os.path.join(d, "BAT0", "capacity"), "57\n")
            write(os.path.join(d, "BAT0", "status"), "Charging\n")
            b = sysinfo.read_battery(d)
            self.assertEqual(b, sysinfo.Battery(57, "Charging"))
            self.assertTrue(b.charging)
            self.assertEqual(sysinfo.battery_icon(b), "battery-level-50-charging-symbolic")

    def test_full_battery_icon(self):
        self.assertEqual(
            sysinfo.battery_icon(sysinfo.Battery(100, "Full")), "battery-level-100-symbolic"
        )


class NetworkTests(unittest.TestCase):
    def test_none_when_everything_down(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "lo", "operstate"), "unknown\n")
            write(os.path.join(d, "eth0", "operstate"), "down\n")
            self.assertEqual(sysinfo.read_network(d).kind, "none")

    def test_wired_preferred_over_wifi(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "eth0", "operstate"), "up\n")
            write(os.path.join(d, "wlan0", "operstate"), "up\n")
            os.makedirs(os.path.join(d, "wlan0", "wireless"))
            state = sysinfo.read_network(d)
            self.assertEqual((state.kind, state.interface), ("wired", "eth0"))

    def test_wifi(self):
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "wlan0", "operstate"), "up\n")
            os.makedirs(os.path.join(d, "wlan0", "wireless"))
            self.assertEqual(sysinfo.read_network(d).icon, "network-wireless-symbolic")


class VolumeTests(unittest.TestCase):
    def test_parse(self):
        v = sysinfo.parse_wpctl_volume("Volume: 0.45\n")
        self.assertEqual((v.percent, v.muted), (45, False))
        self.assertEqual(v.icon, "audio-volume-medium-symbolic")

    def test_muted(self):
        v = sysinfo.parse_wpctl_volume("Volume: 0.80 [MUTED]\n")
        self.assertTrue(v.muted)
        self.assertEqual(v.icon, "audio-volume-muted-symbolic")

    def test_garbage(self):
        self.assertIsNone(sysinfo.parse_wpctl_volume("no sink"))


if __name__ == "__main__":
    unittest.main()
