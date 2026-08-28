"""Unit tests for descriptions.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "custom_components" / "telegraf_bridge"))

from descriptions import SENSOR_DESCRIPTIONS, describe_metric  # noqa: E402


class DescribeMetricTests(unittest.TestCase):
    def test_flat_metric_lookup(self):
        description, gpu_index = describe_metric("cpu_usage")
        self.assertEqual(description.label, "CPU Usage")
        self.assertIsNone(gpu_index)

    def test_indexed_gpu_metric_normalizes_to_flat_description(self):
        description, gpu_index = describe_metric("gpu0_temp")
        self.assertEqual(gpu_index, "0")
        self.assertEqual(description.label, "GPU 0 Temperature")
        self.assertEqual(description.unit, SENSOR_DESCRIPTIONS["gpu_temp"].unit)

    def test_unknown_metric_raises(self):
        with self.assertRaises(KeyError):
            describe_metric("not_a_real_metric")


if __name__ == "__main__":
    unittest.main()
