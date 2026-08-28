"""Unit tests for sensor.py, stubbing homeassistant.* the same way
test_coordinator.py and test_config_flow.py do (no real HA package
installed - see repo memory telegraf-bridge-dev-workflow.md)."""

from __future__ import annotations

import asyncio
import re
import sys
import types
import unicodedata
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


def simple_slugify(text: str) -> str:
    """Rough approximation of homeassistant.util.slugify, enough to verify
    entity_id compatibility expectations in tests."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text


def install_homeassistant_stubs(stubbed_modules: dict[str, object]) -> types.SimpleNamespace:
    def ensure_stub_module(module_name: str, *, package: bool = False) -> types.ModuleType:
        # Always create a fresh module, even if one already exists in
        # sys.modules from another test file's collection-time stubbing -
        # reusing it would let that file's later mutations leak into
        # already-loaded modules here that still hold a direct reference.
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

    recorder = types.SimpleNamespace(dispatcher_sends=[], connections=[])

    async def async_subscribe(hass, topic, callback_fn, *a, **kw):
        return lambda: None

    def async_dispatcher_send(hass, signal, *args) -> None:
        recorder.dispatcher_sends.append((signal, args))
        for sig, cb in recorder.connections:
            if sig == signal:
                cb(*args)

    def async_dispatcher_connect(hass, signal, target):
        recorder.connections.append((signal, target))
        return lambda: recorder.connections.remove((signal, target))

    def async_track_time_interval(hass, action, interval):
        return lambda: None

    def callback_decorator(func):
        return func

    class DeviceInfo(dict):
        pass

    class ConfigEntry:
        def __init__(self, entry_id, data=None, options=None):
            self.entry_id = entry_id
            self.data = data or {}
            self.options = options or {}
            self._on_unload = []

        def async_on_unload(self, func):
            self._on_unload.append(func)

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

    AddEntitiesCallback = object

    mqtt_mod.async_subscribe = async_subscribe
    sensor_mod.SensorEntity = SensorEntity
    sensor_mod.SensorDeviceClass = SensorDeviceClass
    sensor_mod.SensorStateClass = SensorStateClass
    config_entries_mod.ConfigEntry = ConfigEntry
    core_mod.HomeAssistant = HomeAssistant
    core_mod.callback = callback_decorator
    device_registry_mod.DeviceInfo = DeviceInfo
    dispatcher_mod.async_dispatcher_send = async_dispatcher_send
    dispatcher_mod.async_dispatcher_connect = async_dispatcher_connect
    event_mod.async_track_time_interval = async_track_time_interval
    storage_mod.Store = FakeStore
    entity_platform_mod.AddEntitiesCallback = AddEntitiesCallback

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
    """Run a coroutine immediately if no event loop is running (plain
    sync unittest.TestCase), otherwise schedule it on the running loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.create_task(coro)


def make_hass():
    hass = types.SimpleNamespace(data={})
    hass.async_create_task = _run_or_schedule
    return hass


def make_entry(entry_id="entry-1", data=None, options=None):
    return types.SimpleNamespace(
        entry_id=entry_id, data=data or {}, options=options or {}, _on_unload=[],
        async_on_unload=lambda func: None,
    )


class SensorAttributesTests(unittest.TestCase):
    def setUp(self):
        self.hass = make_hass()
        self.entry = make_entry()
        self.coordinator = coordinator_module.TelegrafBridgeCoordinator(self.hass, self.entry)
        self.coordinator.hostnames["tower"] = "Tower"

    def test_unique_id_and_basic_attributes(self):
        entity = sensor_module.TelegrafBridgeSensor(self.coordinator, "tower", "cpu_usage")
        self.assertEqual(entity._attr_unique_id, "tower_cpu_usage")
        self.assertEqual(entity._attr_name, "CPU Usage")
        self.assertEqual(entity._attr_native_unit_of_measurement, "%")
        self.assertIsNone(entity._attr_device_class)
        self.assertEqual(entity._attr_state_class, "measurement")

    def test_gpu_indexed_metric_gets_per_gpu_label(self):
        entity = sensor_module.TelegrafBridgeSensor(self.coordinator, "tower", "gpu0_temp")
        self.assertEqual(entity._attr_unique_id, "tower_gpu0_temp")
        self.assertEqual(entity._attr_name, "GPU 0 Temperature")
        self.assertEqual(entity._attr_device_class, "temperature")

    def test_native_value_reflects_coordinator_state(self):
        entity = sensor_module.TelegrafBridgeSensor(self.coordinator, "tower", "cpu_usage")
        self.assertIsNone(entity.native_value)

        self.coordinator._apply_metrics("tower", {"cpu_usage": 42.0}, now=1000.0)
        self.assertEqual(entity.native_value, 42.0)

    def test_availability_reflects_coordinator(self):
        entity = sensor_module.TelegrafBridgeSensor(self.coordinator, "tower", "cpu_usage")
        self.assertFalse(entity.available)
        self.coordinator._apply_metrics("tower", {"cpu_usage": 42.0}, now=__import__("time").time())
        self.assertTrue(entity.available)


class SensorUpdateSignalTests(unittest.IsolatedAsyncioTestCase):
    async def test_added_to_hass_subscribes_and_write_state_on_update(self):
        hass = make_hass()
        entry = make_entry()
        coordinator = coordinator_module.TelegrafBridgeCoordinator(hass, entry)
        entity = sensor_module.TelegrafBridgeSensor(coordinator, "tower", "cpu_usage")
        entity.hass = hass

        await entity.async_added_to_hass()
        self.assertFalse(hasattr(entity, "_state_written"))

        coordinator._apply_metrics("tower", {"cpu_usage": 55.0}, now=1000.0)
        self.assertEqual(entity._state_written, 1)
        self.assertEqual(entity.native_value, 55.0)


class SetupEntryTests(unittest.IsolatedAsyncioTestCase):
    async def test_adds_entities_for_known_pairs_and_new_discoveries(self):
        recorder.dispatcher_sends.clear()
        recorder.connections.clear()

        hass = make_hass()
        entry = make_entry()
        coordinator = coordinator_module.TelegrafBridgeCoordinator(hass, entry)
        coordinator.known_pairs.add(("tower", "cpu_usage"))
        coordinator.metrics[("tower", "cpu_usage")] = coordinator_module.MetricState(
            value=None, last_updated=None
        )
        hass.data[coordinator_module.DOMAIN] = {entry.entry_id: coordinator}

        added_batches: list[list] = []

        def async_add_entities(entities):
            added_batches.append(list(entities))

        await sensor_module.async_setup_entry(hass, entry, async_add_entities)

        self.assertEqual(len(added_batches), 1)
        self.assertEqual(added_batches[0][0]._attr_unique_id, "tower_cpu_usage")

        coordinator._apply_metrics("pihole", {"cpu_temp": 40.0}, now=1000.0)
        self.assertEqual(len(added_batches), 2)
        self.assertEqual(added_batches[1][0]._attr_unique_id, "pihole_cpu_temp")


class EntityIdCompatibilityTests(unittest.TestCase):
    """Verify device-name + entity-name slugs match the existing
    MQTT-discovery-derived entity_ids (Phase 0 decision), for the metrics
    that kept flat naming. GPU metrics intentionally changed - see TODO."""

    def setUp(self):
        self.hass = make_hass()
        self.entry = make_entry()
        self.coordinator = coordinator_module.TelegrafBridgeCoordinator(self.hass, self.entry)

    def _slug_for(self, hostname: str, host_id: str, metric: str) -> str:
        self.coordinator.hostnames[host_id] = hostname
        entity = sensor_module.TelegrafBridgeSensor(self.coordinator, host_id, metric)
        return simple_slugify(f"{hostname} {entity._attr_name}")

    def test_tower_cpu_usage(self):
        self.assertEqual(self._slug_for("Tower", "tower", "cpu_usage"), "tower_cpu_usage")

    def test_desktop_strix_ram_usage(self):
        self.assertEqual(
            self._slug_for("Desktop-STRIX", "desktop_strix", "ram_usage"),
            "desktop_strix_ram_usage",
        )

    def test_framework_13_battery(self):
        self.assertEqual(
            self._slug_for("Framework_13", "framework_13", "battery"),
            "framework_13_battery",
        )

    def test_pihole_cpu_temp(self):
        self.assertEqual(
            self._slug_for("pihole", "pihole", "cpu_temp"), "pihole_cpu_temperature"
        )

    def test_openwrt_dns_latency(self):
        self.assertEqual(
            self._slug_for("openwrt", "openwrt", "dns_latency"), "openwrt_dns_latency"
        )


if __name__ == "__main__":
    unittest.main()
