"""End-to-end entity lifecycle tests: simulate MQTT messages flowing through
the coordinator and verify sensor.py entities appear, update, and go
unavailable on staleness - stubbing homeassistant.* the same way the other
test files do (no real HA package installed, and no
pytest-homeassistant-custom-component available - see repo memory
telegraf-bridge-dev-workflow.md)."""

from __future__ import annotations

import asyncio
import json
import sys
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "telegraf_bridge"
_MISSING = object()


def _install_stub_module(
    stubbed_modules: dict[str, object], module_name: str, module: types.ModuleType
) -> None:
    stubbed_modules.setdefault(module_name, sys.modules.get(module_name, _MISSING))
    sys.modules[module_name] = module


def restore_stubbed_modules(stubbed_modules: dict[str, object]) -> None:
    for module_name, previous in reversed(list(stubbed_modules.items())):
        if previous is _MISSING:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous


class FakeStore:
    def __init__(self, hass, version, key) -> None:
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


def install_homeassistant_stubs(stubbed_modules: dict[str, object]) -> types.SimpleNamespace:
    def ensure_stub_module(module_name: str, *, package: bool = False) -> types.ModuleType:
        module = types.ModuleType(module_name)
        _install_stub_module(stubbed_modules, module_name, module)
        if package:
            module.__path__ = []
        return module

    homeassistant = ensure_stub_module("homeassistant", package=True)
    components = ensure_stub_module("homeassistant.components", package=True)
    helpers = ensure_stub_module("homeassistant.helpers", package=True)

    mqtt_mod = ensure_stub_module("homeassistant.components.mqtt")
    sensor_mod = ensure_stub_module("homeassistant.components.sensor")
    config_entries_mod = ensure_stub_module("homeassistant.config_entries")
    core_mod = ensure_stub_module("homeassistant.core")
    device_registry_mod = ensure_stub_module("homeassistant.helpers.device_registry")
    dispatcher_mod = ensure_stub_module("homeassistant.helpers.dispatcher")
    event_mod = ensure_stub_module("homeassistant.helpers.event")
    storage_mod = ensure_stub_module("homeassistant.helpers.storage")
    entity_platform_mod = ensure_stub_module("homeassistant.helpers.entity_platform")

    recorder = types.SimpleNamespace(connections=[], interval_callback=None)

    async def async_subscribe(hass, topic, callback_fn, *a, **kw):
        recorder.mqtt_callback = callback_fn
        return lambda: None

    def async_dispatcher_send(hass, signal, *args) -> None:
        for sig, cb in list(recorder.connections):
            if sig == signal:
                cb(*args)

    def async_dispatcher_connect(hass, signal, target):
        recorder.connections.append((signal, target))
        return lambda: recorder.connections.remove((signal, target))

    def async_track_time_interval(hass, action, interval):
        recorder.interval_callback = action
        return lambda: None

    class DeviceInfo(dict):
        pass

    class ConfigEntry:
        def __init__(self, entry_id, data=None, options=None):
            self.entry_id = entry_id
            self.data = data or {}
            self.options = options or {}

        def async_on_unload(self, func) -> None:
            pass

    class HomeAssistant:
        pass

    class SensorDeviceClass(str):
        pass

    class SensorStateClass(str):
        pass

    class SensorEntity:
        def async_on_remove(self, func) -> None:
            self._on_remove_funcs = getattr(self, "_on_remove_funcs", [])
            self._on_remove_funcs.append(func)

        def async_write_ha_state(self) -> None:
            self._state_written = getattr(self, "_state_written", 0) + 1

    mqtt_mod.async_subscribe = async_subscribe
    sensor_mod.SensorEntity = SensorEntity
    sensor_mod.SensorDeviceClass = SensorDeviceClass
    sensor_mod.SensorStateClass = SensorStateClass
    config_entries_mod.ConfigEntry = ConfigEntry
    core_mod.HomeAssistant = HomeAssistant
    core_mod.callback = lambda func: func
    device_registry_mod.DeviceInfo = DeviceInfo
    dispatcher_mod.async_dispatcher_send = async_dispatcher_send
    dispatcher_mod.async_dispatcher_connect = async_dispatcher_connect
    event_mod.async_track_time_interval = async_track_time_interval
    storage_mod.Store = FakeStore
    entity_platform_mod.AddEntitiesCallback = object

    homeassistant.components = components
    homeassistant.helpers = helpers
    components.mqtt = mqtt_mod
    components.sensor = sensor_mod
    helpers.device_registry = device_registry_mod
    helpers.dispatcher = dispatcher_mod
    helpers.event = event_mod
    helpers.storage = storage_mod
    helpers.entity_platform = entity_platform_mod

    return recorder


def load_modules(stubbed_modules: dict[str, object]):
    import importlib.util

    package_name = "telegraf_bridge"
    package_mod = types.ModuleType(package_name)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, package_name, package_mod)

    loaded = {}
    for submodule in ("const", "parsers", "descriptions", "coordinator", "sensor"):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{submodule}", PACKAGE_ROOT / f"{submodule}.py"
        )
        module = importlib.util.module_from_spec(spec)
        _install_stub_module(stubbed_modules, f"{package_name}.{submodule}", module)
        spec.loader.exec_module(module)
        loaded[submodule] = module
    return loaded


stubbed_modules: dict[str, object] = {}
recorder = install_homeassistant_stubs(stubbed_modules)
modules = load_modules(stubbed_modules)
coordinator_module = modules["coordinator"]
sensor_module = modules["sensor"]


def tearDownModule() -> None:
    restore_stubbed_modules(stubbed_modules)


def _run_or_schedule(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.create_task(coro)


def make_hass():
    hass = types.SimpleNamespace(data={})
    hass.async_create_task = _run_or_schedule
    return hass


def make_entry(entry_id="entry-1"):
    return types.SimpleNamespace(
        entry_id=entry_id, data={}, options={}, async_on_unload=lambda func: None
    )


class EntityLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        recorder.connections.clear()
        self.hass = make_hass()
        self.entry = make_entry()
        self.coordinator = coordinator_module.TelegrafBridgeCoordinator(self.hass, self.entry)
        await self.coordinator.async_setup()
        self.hass.data[coordinator_module.DOMAIN] = {self.entry.entry_id: self.coordinator}

        self.added_entities: list = []

        def async_add_entities(entities):
            self.added_entities.extend(entities)

        await sensor_module.async_setup_entry(self.hass, self.entry, async_add_entities)

    async def _publish(self, topic: str, payload: dict) -> None:
        await self.coordinator._async_process_message(topic, json.dumps(payload))

    async def test_entity_appears_on_first_message(self):
        self.assertEqual(self.added_entities, [])

        await self._publish(
            "systems/Server/cpu",
            {"fields": {"usage_idle": 70}, "tags": {"cpu": "cpu-total"}, "name": "cpu"},
        )

        self.assertEqual(len(self.added_entities), 1)
        entity = self.added_entities[0]
        self.assertEqual(entity._attr_unique_id, "server_cpu_usage")
        self.assertEqual(entity.native_value, 30)

    async def test_entity_updates_on_subsequent_messages(self):
        await self._publish(
            "systems/Server/cpu",
            {"fields": {"usage_idle": 70}, "tags": {"cpu": "cpu-total"}, "name": "cpu"},
        )
        entity = self.added_entities[0]
        entity.hass = self.hass
        await entity.async_added_to_hass()

        await self._publish(
            "systems/Server/cpu",
            {"fields": {"usage_idle": 40}, "tags": {"cpu": "cpu-total"}, "name": "cpu"},
        )

        self.assertEqual(entity.native_value, 60)
        self.assertEqual(entity._state_written, 1)
        # Still only one entity - the second message updated it in place.
        self.assertEqual(len(self.added_entities), 1)

    async def test_entity_goes_unavailable_after_staleness_check(self):
        await self._publish(
            "systems/Server/cpu",
            {"fields": {"usage_idle": 70}, "tags": {"cpu": "cpu-total"}, "name": "cpu"},
        )
        entity = self.added_entities[0]
        entity.hass = self.hass
        await entity.async_added_to_hass()
        self.assertTrue(entity.available)

        # Simulate time passing beyond STALE_AFTER_SECONDS, then the
        # periodic staleness check firing (as async_track_time_interval would).
        state = self.coordinator.metrics[("server", "cpu_usage")]
        state.last_updated -= coordinator_module.STALE_AFTER_SECONDS + 1
        recorder.interval_callback(None)

        self.assertFalse(entity.available)
        self.assertEqual(entity._state_written, 1)

    async def test_persisted_pairs_create_unavailable_entities_before_first_message(self):
        # Simulate a fresh coordinator/platform restarting with storage
        # already populated from a previous run.
        hass = make_hass()
        entry = make_entry(entry_id="entry-2")
        coordinator = coordinator_module.TelegrafBridgeCoordinator(hass, entry)
        coordinator.store._data = {"known_pairs": [["server", "cpu_usage"]]}
        await coordinator.async_setup()
        hass.data[coordinator_module.DOMAIN] = {entry.entry_id: coordinator}

        added: list = []
        await sensor_module.async_setup_entry(hass, entry, lambda entities: added.extend(entities))

        self.assertEqual(len(added), 1)
        self.assertFalse(added[0].available)
        self.assertIsNone(added[0].native_value)


if __name__ == "__main__":
    unittest.main()
