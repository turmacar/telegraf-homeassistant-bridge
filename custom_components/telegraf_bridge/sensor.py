"""Sensor platform for Telegraf Bridge.

Entities are created reactively as the coordinator discovers new
(host_id, metric) pairs (SIGNAL_NEW_ENTITY), and update themselves via a
per-pair dispatcher signal (signal_update) rather than polling - this is a
push (MQTT) integration, so no CoordinatorEntity/DataUpdateCoordinator here.
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_NEW_ENTITY
from .coordinator import TelegrafBridgeCoordinator, signal_update
from .descriptions import describe_metric


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Telegraf Bridge sensor entities as they're discovered."""
    coordinator: TelegrafBridgeCoordinator = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _async_new_entity(host_id: str, metric: str) -> None:
        async_add_entities([TelegrafBridgeSensor(coordinator, host_id, metric)])

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_NEW_ENTITY, _async_new_entity)
    )

    # Pairs the coordinator already knew about before this platform loaded
    # (e.g. restored from persisted storage during coordinator.async_setup).
    async_add_entities(
        TelegrafBridgeSensor(coordinator, host_id, metric)
        for host_id, metric in coordinator.known_pairs
    )


class TelegrafBridgeSensor(SensorEntity):
    """A single telegraf metric for a single host."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: TelegrafBridgeCoordinator, host_id: str, metric: str) -> None:
        self._coordinator = coordinator
        self._host_id = host_id
        self._metric = metric

        self._attr_unique_id = f"{host_id}_{metric}"
        self._attr_device_info = coordinator.device_info_for(host_id)

        description, _gpu_index = describe_metric(metric)
        self._attr_name = description.label
        self._attr_icon = description.icon
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = (
            SensorDeviceClass(description.device_class) if description.device_class else None
        )
        self._attr_state_class = (
            SensorStateClass(description.state_class) if description.state_class else None
        )

    @property
    def native_value(self):
        state = self._coordinator.metrics.get((self._host_id, self._metric))
        return state.value if state else None

    @property
    def available(self) -> bool:
        return self._coordinator.is_available(self._host_id, self._metric)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_update(self._host_id, self._metric),
                self._async_handle_update,
            )
        )

    @callback
    def _async_handle_update(self) -> None:
        self.async_write_ha_state()
