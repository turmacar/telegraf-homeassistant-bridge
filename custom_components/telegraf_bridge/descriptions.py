"""Sensor metadata table, ported from gen_nodered_flow.py's baseSensors/
extraSensors/gpuSensors. Plain dataclasses (no Home Assistant import) so
parsers.py and its tests stay HA-free; sensor.py (Phase 5) converts these
into SensorEntityDescription objects when building entities.

Metric names ending in a GPU index (e.g. "gpu0_temp") aren't listed
directly - use `describe_metric()` which normalizes "gpu{N}_*" to the
flat "gpu_*" description.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SensorDescription:
    label: str
    icon: str
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None


# Present on every host.
BASE_SENSOR_DESCRIPTIONS: dict[str, SensorDescription] = {
    "cpu_usage": SensorDescription("CPU Usage", "mdi:cpu-64-bit", "%", state_class="measurement"),
    "ram_usage": SensorDescription("RAM Usage", "mdi:memory", "%", state_class="measurement"),
    "disk_root_usage": SensorDescription(
        "Root Disk Usage", "mdi:harddisk", "%", state_class="measurement"
    ),
    "uptime": SensorDescription(
        "Uptime", "mdi:timer-outline", "s", device_class="duration", state_class="total_increasing"
    ),
}

# Present only on hosts that publish the corresponding measurement/tags.
EXTRA_SENSOR_DESCRIPTIONS: dict[str, SensorDescription] = {
    "docker_running": SensorDescription("Docker Containers", "mdi:docker", state_class="measurement"),
    "gpu_temp": SensorDescription(
        "GPU Temperature", "mdi:thermometer", "°C", device_class="temperature", state_class="measurement"
    ),
    "gpu_usage": SensorDescription("GPU Usage", "mdi:expansion-card", "%", state_class="measurement"),
    "gpu_vram_used": SensorDescription(
        "GPU VRAM Used", "mdi:expansion-card", "MiB", state_class="measurement"
    ),
    "gpu_name": SensorDescription("GPU Model", "mdi:expansion-card"),
    "cpu_temp": SensorDescription(
        "CPU Temperature", "mdi:thermometer", "°C", device_class="temperature", state_class="measurement"
    ),
    "battery": SensorDescription(
        "Battery", "mdi:battery", "%", device_class="battery", state_class="measurement"
    ),
    "wan_rx_mbps": SensorDescription(
        "WAN Download", "mdi:download-network", "Mbit/s", device_class="data_rate", state_class="measurement"
    ),
    "wan_tx_mbps": SensorDescription(
        "WAN Upload", "mdi:upload-network", "Mbit/s", device_class="data_rate", state_class="measurement"
    ),
    "dns_latency": SensorDescription(
        "DNS Latency", "mdi:dns", "ms", device_class="duration", state_class="measurement"
    ),
}

SENSOR_DESCRIPTIONS: dict[str, SensorDescription] = {
    **BASE_SENSOR_DESCRIPTIONS,
    **EXTRA_SENSOR_DESCRIPTIONS,
}

_GPU_METRIC_RE = re.compile(r"^gpu(\d+)_(temp|usage|vram_used|name)$")


def describe_metric(metric: str) -> tuple[SensorDescription, str | None]:
    """Look up a metric's SensorDescription, normalizing indexed GPU metrics
    (e.g. "gpu0_temp") to their flat description ("gpu_temp"), with a
    per-GPU label suffix (e.g. "GPU 0 Temperature").

    Returns (description, gpu_index_or_None). Raises KeyError if unknown.
    """
    if metric in SENSOR_DESCRIPTIONS:
        return SENSOR_DESCRIPTIONS[metric], None

    match = _GPU_METRIC_RE.match(metric)
    if match:
        index, suffix = match.groups()
        base = SENSOR_DESCRIPTIONS[f"gpu_{suffix}"]
        label_parts = base.label.split(" ", 1)
        label = f"{label_parts[0]} {index} {label_parts[1]}" if len(label_parts) > 1 else base.label
        return SensorDescription(label, base.icon, base.unit, base.device_class, base.state_class), index

    raise KeyError(metric)
