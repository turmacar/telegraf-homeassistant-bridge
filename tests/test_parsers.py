"""Unit tests for parsers.py, using real telegraf payloads captured
2026-08-28 (see tests/fixtures/telegraf_payloads.py)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "custom_components" / "telegraf_bridge"))

from parsers import (  # noqa: E402
    NetSample,
    average_dns_latency,
    parse_battery,
    parse_cpu,
    parse_disk,
    parse_dns_query_sample,
    parse_docker,
    parse_mem,
    parse_measurement,
    parse_net_rate,
    parse_nvidia_smi,
    parse_sensors,
    parse_system,
    parse_temp,
)

from tests.fixtures.telegraf_payloads import PAYLOADS


def item(key: str, index: int = 0) -> dict:
    return PAYLOADS[key][index]


class ParseCpuTests(unittest.TestCase):
    def test_cpu_total_reports_usage(self):
        payload = item("cpu_tower")
        result = parse_cpu(payload["tags"], payload["fields"])
        self.assertIn("cpu_usage", result)
        self.assertAlmostEqual(result["cpu_usage"], 100 - payload["fields"]["usage_idle"], places=1)

    def test_non_total_cpu_ignored(self):
        result = parse_cpu({"cpu": "cpu0"}, {"usage_idle": 50})
        self.assertEqual(result, {})


class ParseMemTests(unittest.TestCase):
    def test_ram_usage(self):
        payload = item("mem_framework")
        result = parse_mem(payload["fields"])
        self.assertEqual(result["ram_usage"], round(payload["fields"]["used_percent"], 1))


class ParseDiskTests(unittest.TestCase):
    def test_root_path_reports_usage(self):
        payload = item("disk_root_tower")
        result = parse_disk(payload["tags"], payload["fields"])
        self.assertEqual(result["disk_root_usage"], round(payload["fields"]["used_percent"], 1))

    def test_non_root_path_ignored(self):
        result = parse_disk({"path": "/boot"}, {"used_percent": 10})
        self.assertEqual(result, {})


class ParseSystemTests(unittest.TestCase):
    def test_uptime_message(self):
        payload = item("system_uptime_tower")
        result = parse_system(payload["fields"])
        self.assertEqual(result, {"uptime": payload["fields"]["uptime"]})

    def test_load_only_message_does_not_zero_uptime(self):
        payload = item("system_load_tower")
        result = parse_system(payload["fields"])
        self.assertEqual(result, {})

    def test_uptime_format_only_message_ignored(self):
        payload = item("system_uptime_format_tower")
        result = parse_system(payload["fields"])
        self.assertEqual(result, {})


class ParseDockerTests(unittest.TestCase):
    def test_docker_running(self):
        payload = item("docker_tower")
        result = parse_docker(payload["fields"])
        self.assertEqual(result["docker_running"], payload["fields"]["n_containers_running"])


class ParseNvidiaSmiTests(unittest.TestCase):
    def test_single_gpu_uses_flat_keys(self):
        payload = item("nvidia_smi_desktop")
        result = parse_nvidia_smi(payload["tags"], payload["fields"], multi_gpu=False)
        self.assertEqual(result["gpu_temp"], round(payload["fields"]["temperature_gpu"], 1))
        self.assertEqual(result["gpu_usage"], round(payload["fields"]["utilization_gpu"], 1))
        self.assertEqual(result["gpu_vram_used"], round(payload["fields"]["memory_used"]))
        self.assertEqual(result["gpu_name"], "GeForce RTX 3070 Ti")

    def test_multi_gpu_uses_indexed_keys(self):
        gpu0 = item("nvidia_smi_tower", 0)
        gpu1 = item("nvidia_smi_tower", 1)
        self.assertEqual(gpu0["tags"]["index"], "0")
        self.assertEqual(gpu1["tags"]["index"], "1")

        result0 = parse_nvidia_smi(gpu0["tags"], gpu0["fields"], multi_gpu=True)
        result1 = parse_nvidia_smi(gpu1["tags"], gpu1["fields"], multi_gpu=True)
        self.assertIn("gpu0_temp", result0)
        self.assertIn("gpu1_temp", result1)
        self.assertNotIn("gpu1_temp", result0)


class ParseSensorsTests(unittest.TestCase):
    def test_amd_tctl_is_cpu_temp(self):
        payload = item("sensors_desktop_tctl")
        result = parse_sensors(payload["tags"], payload["fields"])
        self.assertEqual(result["cpu_temp"], round(payload["fields"]["temp_input"], 1))

    def test_non_cpu_feature_ignored(self):
        # sensors_framework[0] is amdgpu vddgfx voltage, not a CPU temp
        payload = item("sensors_framework", 0)
        result = parse_sensors(payload["tags"], payload["fields"])
        self.assertEqual(result, {})


class ParseTempTests(unittest.TestCase):
    def test_pi_cpu_thermal_reports_cpu_temp(self):
        payload = item("temp_ha_pi", 0)
        self.assertEqual(payload["tags"]["sensor"], "cpu_thermal")
        result = parse_temp(payload["tags"], payload["fields"])
        self.assertEqual(result["cpu_temp"], round(payload["fields"]["temp"], 1))

    def test_pi_non_cpu_sensor_ignored(self):
        # temp_ha_pi[1] is rp1_adc, not the CPU
        payload = item("temp_ha_pi", 1)
        self.assertEqual(payload["tags"]["sensor"], "rp1_adc")
        result = parse_temp(payload["tags"], payload["fields"])
        self.assertEqual(result, {})

    def test_pihole_cpu_thermal(self):
        payload = item("temp_pihole", 0)
        result = parse_temp(payload["tags"], payload["fields"])
        self.assertIn("cpu_temp", result)


class ParseBatteryTests(unittest.TestCase):
    def test_battery_measurement(self):
        payload = item("battery_framework")
        result = parse_battery("battery", payload["tags"], payload["fields"])
        self.assertEqual(result["battery"], round(payload["fields"]["value"]))

    def test_file_with_battery_override(self):
        result = parse_battery("file", {"name_override": "battery"}, {"value": 42})
        self.assertEqual(result, {"battery": 42})

    def test_other_file_ignored(self):
        result = parse_battery("file", {"name_override": "something_else"}, {"value": 42})
        self.assertEqual(result, {})


class ParseNetRateTests(unittest.TestCase):
    def test_first_sample_has_no_previous_returns_no_metrics(self):
        payload = item("net_openwrt")
        result, sample = parse_net_rate(payload["tags"], payload["fields"], None, now=1000.0)
        self.assertEqual(result, {})
        self.assertIsInstance(sample, NetSample)

    def test_second_sample_computes_rate(self):
        payload = item("net_openwrt")
        previous = NetSample(
            timestamp=1000.0,
            bytes_recv=payload["fields"]["bytes_recv"] - 1_000_000,
            bytes_sent=payload["fields"]["bytes_sent"] - 500_000,
        )
        result, sample = parse_net_rate(payload["tags"], payload["fields"], previous, now=1010.0)
        self.assertIn("wan_rx_mbps", result)
        self.assertIn("wan_tx_mbps", result)
        self.assertGreater(result["wan_rx_mbps"], 0)

    def test_non_eth0_interface_ignored(self):
        result, sample = parse_net_rate({"interface": "wlan0"}, {"bytes_recv": 1, "bytes_sent": 1}, None, now=1.0)
        self.assertEqual(result, {})
        self.assertIsNone(sample)


class DnsQueryTests(unittest.TestCase):
    def test_extracts_query_time(self):
        payload = item("dns_query_openwrt", 0)
        self.assertEqual(
            parse_dns_query_sample(payload["fields"]), payload["fields"]["query_time_ms"]
        )

    def test_average_across_resolvers(self):
        times = [parse_dns_query_sample(p["fields"]) for p in PAYLOADS["dns_query_openwrt"]]
        avg = average_dns_latency(times)
        self.assertEqual(avg, round(sum(times) / len(times)))

    def test_average_of_empty_is_none(self):
        self.assertIsNone(average_dns_latency([]))


class DispatcherTests(unittest.TestCase):
    def test_parse_measurement_routes_cpu(self):
        payload = item("cpu_tower")
        result = parse_measurement("cpu", payload["tags"], payload["fields"])
        self.assertIn("cpu_usage", result)

    def test_parse_measurement_unknown_returns_empty(self):
        self.assertEqual(parse_measurement("kernel", {}, {}), {})


if __name__ == "__main__":
    unittest.main()
