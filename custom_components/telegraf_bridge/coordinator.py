"""MQTT subscription and entity lifecycle for Telegraf Bridge.

Subscribes to the telegraf MQTT topic, routes each message through
parsers.py, tracks per-(host_id, metric) state, and notifies sensor.py
(via dispatcher signals) of new and updated entities. Owns all the stateful
bits parsers.py deliberately doesn't: net rate previous-sample tracking,
dns_query rolling-window averaging, and persistence of known (host_id,
metric) pairs across HA restarts.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_TOPIC,
    DNS_QUERY_WINDOW_SIZE,
    DOMAIN,
    SIGNAL_NEW_ENTITY,
    STALE_AFTER_SECONDS,
    STALENESS_CHECK_INTERVAL_SECONDS,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .parsers import (
    MetricValue,
    NetSample,
    average_dns_latency,
    parse_dns_query_sample,
    parse_measurement,
    parse_net_rate,
)

_LOGGER = logging.getLogger(__name__)


def host_id_from_hostname(hostname: str) -> str:
    """Match Node-RED's host_id derivation so entity_ids line up with the
    existing MQTT-discovery-derived ones (e.g. "Desktop-PC" -> "desktop_pc")."""
    return hostname.lower().replace("-", "_").replace(" ", "_")


def signal_update(host_id: str, metric: str) -> str:
    """Per-(host_id, metric) dispatcher signal an existing entity listens on."""
    return f"{DOMAIN}_update_{host_id}_{metric}"


@dataclass
class MetricState:
    value: MetricValue | None
    last_updated: float | None


class TelegrafBridgeCoordinator:
    """Owns MQTT subscription, parsing state, and entity lifecycle."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}")
        self.metrics: dict[tuple[str, str], MetricState] = {}
        self.known_pairs: set[tuple[str, str]] = set()
        self.hostnames: dict[str, str] = {}
        self._net_samples: dict[str, NetSample] = {}
        self._dns_samples: dict[str, list[float]] = {}
        self._unsub_mqtt = None
        self._unsub_interval = None

    async def async_setup(self) -> None:
        """Load persisted (host_id, metric) pairs and subscribe to MQTT."""
        stored = await self.store.async_load()
        if stored:
            for host_id, metric in stored.get("known_pairs", []):
                self.known_pairs.add((host_id, metric))
                self.metrics[(host_id, metric)] = MetricState(value=None, last_updated=None)
                async_dispatcher_send(self.hass, SIGNAL_NEW_ENTITY, host_id, metric)

        topic = self.entry.data.get("topic", DEFAULT_TOPIC)
        self._unsub_mqtt = await mqtt.async_subscribe(self.hass, topic, self._handle_message)
        self._unsub_interval = async_track_time_interval(
            self.hass,
            self._async_check_staleness,
            timedelta(seconds=STALENESS_CHECK_INTERVAL_SECONDS),
        )

    async def async_unload(self) -> None:
        if self._unsub_mqtt:
            self._unsub_mqtt()
        if self._unsub_interval:
            self._unsub_interval()

    def device_info_for(self, host_id: str) -> DeviceInfo:
        """One DeviceInfo per host_id. Name defaults to the raw hostname (not
        host_id) so HA's entity_id slugification matches the existing
        sensor.<host>_* naming - see repo memory ha-mqtt-discovery-entity-id.md.
        Manufacturer/model/name can be overridden via the Options Flow
        (stored in `entry.options["host_overrides"][host_id]`)."""
        override = self.entry.options.get("host_overrides", {}).get(host_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, host_id)},
            name=override.get("name") or self.hostnames.get(host_id, host_id),
            manufacturer=override.get("manufacturer") or None,
            model=override.get("model") or None,
        )

    @callback
    def _handle_message(self, msg) -> None:
        self.hass.async_create_task(self._async_process_message(msg.topic, msg.payload))

    async def _async_process_message(self, topic: str, payload: str) -> None:
        parts = topic.split("/")
        if len(parts) < 3:
            return
        hostname, measurement = parts[1], parts[2]
        host_id = host_id_from_hostname(hostname)
        self.hostnames.setdefault(host_id, hostname)

        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            return

        now = time.time()
        for item in data if isinstance(data, list) else [data]:
            fields = item.get("fields", item)
            tags = item.get("tags", {})
            self._process_item(host_id, measurement, tags, fields, now)

    def _process_item(
        self, host_id: str, measurement: str, tags: dict, fields: dict, now: float
    ) -> None:
        """Dispatch by measurement name only - no hostname special-casing,
        so any host publishing these measurements is picked up automatically."""
        if measurement == "dns_query":
            self._handle_dns_query(host_id, fields, now)
            return

        if measurement == "net":
            metrics, sample = parse_net_rate(
                tags, fields, self._net_samples.get(host_id), now=now
            )
            if sample is not None:
                self._net_samples[host_id] = sample
            self._apply_metrics(host_id, metrics, now)
            return

        metrics = parse_measurement(measurement, tags, fields)
        self._apply_metrics(host_id, metrics, now)

    def _handle_dns_query(self, host_id: str, fields: dict, now: float) -> None:
        sample = parse_dns_query_sample(fields)
        if sample is None:
            return
        window = self._dns_samples.setdefault(host_id, [])
        window.append(sample)
        if len(window) < DNS_QUERY_WINDOW_SIZE:
            return
        avg = average_dns_latency(window)
        window.clear()
        if avg is not None:
            self._apply_metrics(host_id, {"dns_latency": avg}, now)

    def _apply_metrics(self, host_id: str, metrics: dict[str, MetricValue], now: float) -> None:
        newly_added = False
        for metric, value in metrics.items():
            key = (host_id, metric)
            is_new = key not in self.known_pairs
            self.metrics[key] = MetricState(value=value, last_updated=now)
            if is_new:
                self.known_pairs.add(key)
                newly_added = True
                async_dispatcher_send(self.hass, SIGNAL_NEW_ENTITY, host_id, metric)
            async_dispatcher_send(self.hass, signal_update(host_id, metric))
        if newly_added:
            self.hass.async_create_task(self._async_persist())

    async def _async_persist(self) -> None:
        await self.store.async_save(
            {"known_pairs": [list(pair) for pair in self.known_pairs]}
        )

    @callback
    def _async_check_staleness(self, now) -> None:
        """Nudge every known entity to re-evaluate availability. Entities
        compute `available` themselves from `last_updated`; this just makes
        sure they re-render once they cross the staleness threshold."""
        for host_id, metric in self.known_pairs:
            async_dispatcher_send(self.hass, signal_update(host_id, metric))

    def is_available(self, host_id: str, metric: str) -> bool:
        state = self.metrics.get((host_id, metric))
        if state is None or state.last_updated is None:
            return False
        return (time.time() - state.last_updated) < STALE_AFTER_SECONDS
