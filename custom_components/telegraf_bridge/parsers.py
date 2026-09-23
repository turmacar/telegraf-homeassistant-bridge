"""Pure functions translating telegraf MQTT payloads into metric dicts.

Ported from telegraf-homeassistant/scripts/gen_nodered_flow.py's
TRANSFORM_FUNC (Node-RED). Each measurement's fields/tags (as decoded from
telegraf's `data_format = "json"` MQTT payload) map to zero or more
`{metric_name: value}` pairs. No Home Assistant imports here so this module
is testable without a running HA/MQTT stack.

`net` and `dns_query` need state across messages (previous byte counters /
a rolling window of query times) and are intentionally NOT part of the
single-message `parse_measurement` dispatcher below - the coordinator owns
that state and calls `parse_net_rate` / `parse_dns_query_sample` directly.

`nvidia_smi` (real NVML data) and `amd_smi` (amd-smi reshaped via telegraf's
exec + json_v2 to the same measurement/tags/fields, since telegraf has no
native AMD GPU plugin) both key metrics by `tags["index"]`
(gpu0_temp, gpu1_temp,...). `amdgpu_sysfs` is the same idea for hosts with
no amd-smi/ROCm available (e.g. SteamOS): raw amdgpu sysfs node values,
still keyed by `tags["index"]`, converted from native sysfs units.
"""

from __future__ import annotations

from typing import NamedTuple

MetricValue = float | int | str


def parse_cpu(tags: dict, fields: dict) -> dict[str, MetricValue]:
    """CPU usage, only for the aggregate cpu-total tag."""
    if tags.get("cpu") != "cpu-total":
        return {}
    usage_idle = fields.get("usage_idle")
    if usage_idle is None:
        return {}
    return {"cpu_usage": round(100 - usage_idle, 1)}


def parse_mem(fields: dict) -> dict[str, MetricValue]:
    used_percent = fields.get("used_percent")
    if used_percent is None:
        return {}
    return {"ram_usage": round(used_percent, 1)}


def parse_disk(tags: dict, fields: dict) -> dict[str, MetricValue]:
    """Root filesystem usage only."""
    if tags.get("path") != "/":
        return {}
    used_percent = fields.get("used_percent")
    if used_percent is None:
        return {}
    return {"disk_root_usage": round(used_percent, 1)}


def parse_system(fields: dict) -> dict[str, MetricValue]:
    """Uptime only - system also publishes load-only and uptime_format-only
    messages that must not zero out the last known uptime."""
    uptime = fields.get("uptime")
    if uptime is None:
        return {}
    return {"uptime": int(uptime)}


def parse_docker(fields: dict) -> dict[str, MetricValue]:
    running = fields.get("n_containers_running")
    if running is None:
        return {}
    return {"docker_running": running}


def parse_nvidia_smi(tags: dict, fields: dict) -> dict[str, MetricValue]:
    """GPU temp/usage/vram/name, keyed by tags.index (always gpu{index}_*,
    even for single-GPU hosts - simpler than tracking multi-GPU state).
    Shared by both the real `nvidia_smi` plugin and the `amd_smi` exec-based
    equivalent - same fields/tags shape, just a different vendor prefix on
    the name tag."""
    prefix = f"gpu{tags.get('index')}_"
    result: dict[str, MetricValue] = {}
    if fields.get("temperature_gpu") is not None:
        result[f"{prefix}temp"] = round(fields["temperature_gpu"], 1)
    if fields.get("utilization_gpu") is not None:
        result[f"{prefix}usage"] = round(fields["utilization_gpu"], 1)
    if fields.get("memory_used") is not None:
        result[f"{prefix}vram_used"] = round(fields["memory_used"])
    name = tags.get("name")
    if name:
        for vendor_prefix in ("NVIDIA ", "NVIDIA", "AMD ", "AMD"):
            if name.startswith(vendor_prefix):
                name = name.removeprefix(vendor_prefix)
                break
        result[f"{prefix}name"] = name
    return result


def parse_amdgpu_sysfs(tags: dict, fields: dict) -> dict[str, MetricValue]:
    """AMD GPU temp/usage/vram read straight from amdgpu's own sysfs nodes
    (gpu_busy_percent, mem_info_vram_used, temp1_input) - for hosts with no
    amd-smi/ROCm available (e.g. SteamOS). Keyed by tags.index like
    nvidia_smi/amd_smi, but units are native sysfs units (millidegrees C,
    bytes) rather than amd-smi's already-converted values, so conversion
    happens here instead of in the telegraf config."""
    prefix = f"gpu{tags.get('index')}_"
    result: dict[str, MetricValue] = {}
    temp_millidegrees = fields.get("temp1_input")
    if temp_millidegrees is not None:
        result[f"{prefix}temp"] = round(temp_millidegrees / 1000, 1)
    busy_percent = fields.get("gpu_busy_percent")
    if busy_percent is not None:
        result[f"{prefix}usage"] = round(busy_percent, 1)
    vram_bytes = fields.get("mem_info_vram_used")
    if vram_bytes is not None:
        result[f"{prefix}vram_used"] = round(vram_bytes / 1048576)
    return result


def parse_sensors(tags: dict, fields: dict) -> dict[str, MetricValue]:
    """CPU temp via lm-sensors: tctl (AMD), package_id_N (Intel), or
    coretemp chip + physical feature."""
    feature = (tags.get("feature") or "").lower()
    chip = (tags.get("chip") or "").lower()
    is_cpu_temp = (
        feature == "tctl"
        or feature.startswith("package")
        or ("coretemp" in chip and feature.startswith("physical"))
    )
    temp_input = fields.get("temp_input")
    if not is_cpu_temp or temp_input is None:
        return {}
    return {"cpu_temp": round(temp_input, 1)}


def parse_temp(tags: dict, fields: dict) -> dict[str, MetricValue]:
    """CPU temp from [[inputs.temp]] (Raspberry Pi thermal_zone0, or a
    sensor tag containing 'cpu' or 'tctl')."""
    sensor = (tags.get("sensor") or "").lower()
    is_cpu_temp = sensor == "" or any(
        needle in sensor for needle in ("thermal_zone0", "cpu", "tctl")
    )
    temp = fields.get("temp")
    if not is_cpu_temp or temp is None:
        return {}
    return {"cpu_temp": round(temp, 1)}


def parse_battery(measurement: str, tags: dict, fields: dict) -> dict[str, MetricValue]:
    """Battery percent from either the `battery` measurement or
    [[inputs.file]] with name_override = "battery"."""
    if measurement != "battery" and not (
        measurement == "file" and tags.get("name_override") == "battery"
    ):
        return {}
    value = fields.get("value")
    if value is None and fields:
        value = next(iter(fields.values()))
    if value is None:
        return {}
    return {"battery": round(value)}


# Measurements handled by the stateless single-message dispatcher below.
# `net` (needs previous sample) and `dns_query` (needs a rolling window) are
# intentionally excluded - see module docstring.
def parse_measurement(
    measurement: str,
    tags: dict,
    fields: dict,
) -> dict[str, MetricValue]:
    """Dispatch a single telegraf item to the matching parser."""
    if measurement == "cpu":
        return parse_cpu(tags, fields)
    if measurement == "mem":
        return parse_mem(fields)
    if measurement == "disk":
        return parse_disk(tags, fields)
    if measurement == "system":
        return parse_system(fields)
    if measurement == "docker":
        return parse_docker(fields)
    if measurement in ("nvidia_smi", "amd_smi"):
        return parse_nvidia_smi(tags, fields)
    if measurement == "amdgpu_sysfs":
        return parse_amdgpu_sysfs(tags, fields)
    if measurement == "sensors":
        return parse_sensors(tags, fields)
    if measurement == "temp":
        return parse_temp(tags, fields)
    if measurement in ("battery", "file"):
        return parse_battery(measurement, tags, fields)
    return {}


class NetSample(NamedTuple):
    """A previous net byte-counter sample, for rate calculation."""

    timestamp: float
    bytes_recv: float
    bytes_sent: float


def parse_net_rate(
    tags: dict,
    fields: dict,
    previous: NetSample | None,
    *,
    now: float,
) -> tuple[dict[str, MetricValue], NetSample | None]:
    """WAN download/upload rate for a host's eth0 interface, from cumulative
    byte counters between messages. Caller (coordinator) owns `previous` per
    host and must persist the returned NetSample for the next call."""
    if tags.get("interface") != "eth0":
        return {}, previous

    bytes_recv = fields.get("bytes_recv")
    bytes_sent = fields.get("bytes_sent")
    new_sample = (
        NetSample(now, bytes_recv, bytes_sent)
        if bytes_recv is not None and bytes_sent is not None
        else previous
    )

    if previous is None or bytes_recv is None or bytes_sent is None:
        return {}, new_sample

    dt = now - previous.timestamp
    if dt <= 0:
        return {}, new_sample

    rx_mbps = (bytes_recv - previous.bytes_recv) * 8 / 1e6 / dt
    tx_mbps = (bytes_sent - previous.bytes_sent) * 8 / 1e6 / dt

    result: dict[str, MetricValue] = {}
    if rx_mbps >= 0:
        result["wan_rx_mbps"] = round(rx_mbps, 2)
    if tx_mbps >= 0:
        result["wan_tx_mbps"] = round(tx_mbps, 2)
    return result, new_sample


def parse_dns_query_sample(fields: dict) -> float | None:
    """Extract a single dns_query message's query_time_ms. The coordinator
    collects these into a rolling window per host and averages them into
    dns_latency - telegraf publishes one message per resolver, not a batch."""
    return fields.get("query_time_ms")


def average_dns_latency(samples: list[float]) -> int | None:
    """Average a window of dns_query samples into a single dns_latency
    reading (milliseconds, rounded)."""
    if not samples:
        return None
    return round(sum(samples) / len(samples))
