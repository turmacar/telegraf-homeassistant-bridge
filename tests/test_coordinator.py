"""Unit tests for coordinator.py, stubbing homeassistant.* the same way
jackery-homeassistant/tests/test_setup_entry.py does (no real HA package is
installed anywhere on this machine - see repo memory
telegraf-bridge-dev-workflow.md)."""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "custom_components" / "telegraf_bridge"
TEST_MODULE_NAME = "telegraf_bridge_coordinator_test"
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
    """Minimal Store stub: in-memory, records save() calls."""

    def __init__(self, hass, version, key) -> None:
        self.hass = hass
        self.version = version
        self.key = key
        self.saved: list[dict] = []
        self._data: dict | None = None

    async def async_load(self) -> dict | None:
        return self._data

    async def async_save(self, data: dict) -> None:
        self._data = data
        self.saved.append(data)


def install_homeassistant_stubs(stubbed_modules: dict[str, object]) -> types.SimpleNamespace:
    """Install the minimal HA surface coordinator.py touches."""

    def ensure_stub_module(module_name: str, *, package: bool = False) -> types.ModuleType:
        module = sys.modules.get(module_name)
        if not isinstance(module, types.ModuleType):
            module = types.ModuleType(module_name)
            _install_stub_module(stubbed_modules, module_name, module)
        if package and not hasattr(module, "__path__"):
            module.__path__ = []
        return module

    homeassistant = ensure_stub_module("homeassistant", package=True)
    components = ensure_stub_module("homeassistant.components", package=True)
    helpers = ensure_stub_module("homeassistant.helpers", package=True)

    mqtt_mod = ensure_stub_module("homeassistant.components.mqtt")
    config_entries_mod = ensure_stub_module("homeassistant.config_entries")
    core_mod = ensure_stub_module("homeassistant.core")
    device_registry_mod = ensure_stub_module("homeassistant.helpers.device_registry")
    dispatcher_mod = ensure_stub_module("homeassistant.helpers.dispatcher")
    event_mod = ensure_stub_module("homeassistant.helpers.event")
    storage_mod = ensure_stub_module("homeassistant.helpers.storage")

    recorder = types.SimpleNamespace(
        subscribe_calls=[],
        dispatcher_sends=[],
        tracked_intervals=[],
    )

    async def async_subscribe(hass, topic, callback_fn, *args, **kwargs):
        recorder.subscribe_calls.append((topic, callback_fn))
        return lambda: None

    def async_dispatcher_send(hass, signal, *args) -> None:
        recorder.dispatcher_sends.append((signal, args))

    def async_track_time_interval(hass, action, interval):
        recorder.tracked_intervals.append((action, interval))
        return lambda: None

    def callback_decorator(func):
        return func

    class DeviceInfo(dict):
        """Stub DeviceInfo - HA's is a TypedDict-like mapping."""

    class ConfigEntry:
        def __init__(self, entry_id: str, data: dict) -> None:
            self.entry_id = entry_id
            self.data = data

    class HomeAssistant:
        pass

    mqtt_mod.async_subscribe = async_subscribe
    config_entries_mod.ConfigEntry = ConfigEntry
    core_mod.HomeAssistant = HomeAssistant
    core_mod.callback = callback_decorator
    device_registry_mod.DeviceInfo = DeviceInfo
    dispatcher_mod.async_dispatcher_send = async_dispatcher_send
    event_mod.async_track_time_interval = async_track_time_interval
    storage_mod.Store = FakeStore

    homeassistant.components = components
    homeassistant.helpers = helpers
    components.mqtt = mqtt_mod
    helpers.device_registry = device_registry_mod
    helpers.dispatcher = dispatcher_mod
    helpers.event = event_mod
    helpers.storage = storage_mod

    return recorder


def load_coordinator_module(stubbed_modules: dict[str, object]):
    import importlib.util

    package_name = "telegraf_bridge"
    package_mod = types.ModuleType(package_name)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, package_name, package_mod)

    for submodule in ("const", "parsers"):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{submodule}", PACKAGE_ROOT / f"{submodule}.py"
        )
        module = importlib.util.module_from_spec(spec)
        _install_stub_module(stubbed_modules, f"{package_name}.{submodule}", module)
        spec.loader.exec_module(module)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.coordinator", PACKAGE_ROOT / "coordinator.py"
    )
    module = importlib.util.module_from_spec(spec)
    _install_stub_module(stubbed_modules, f"{package_name}.coordinator", module)
    spec.loader.exec_module(module)
    return module


stubbed_modules: dict[str, object] = {}
recorder = install_homeassistant_stubs(stubbed_modules)
coordinator_module = load_coordinator_module(stubbed_modules)


def tearDownModule() -> None:
    restore_stubbed_modules(stubbed_modules)


def make_hass():
    hass = types.SimpleNamespace(data={})
    hass.async_create_task = lambda coro: asyncio.ensure_future(coro)
    return hass


def make_entry(entry_id="entry-1", data=None):
    return types.SimpleNamespace(entry_id=entry_id, data=data or {})


class CoordinatorSetupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        recorder.subscribe_calls.clear()
        recorder.dispatcher_sends.clear()
        recorder.tracked_intervals.clear()

    async def test_async_setup_subscribes_to_default_topic(self):
        coordinator = coordinator_module.TelegrafBridgeCoordinator(make_hass(), make_entry())
        await coordinator.async_setup()
        self.assertEqual(len(recorder.subscribe_calls), 1)
        topic, _ = recorder.subscribe_calls[0]
        self.assertEqual(topic, "systems/#")

    async def test_async_setup_recreates_entities_from_storage(self):
        coordinator = coordinator_module.TelegrafBridgeCoordinator(make_hass(), make_entry())
        coordinator.store._data = {"known_pairs": [["tower", "cpu_usage"]]}
        await coordinator.async_setup()

        self.assertIn(("tower", "cpu_usage"), coordinator.known_pairs)
        self.assertFalse(coordinator.is_available("tower", "cpu_usage"))
        new_entity_sends = [s for s in recorder.dispatcher_sends if s[0] == "telegraf_bridge_new_entity"]
        self.assertEqual(new_entity_sends[0][1], ("tower", "cpu_usage"))


class ProcessMessageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        recorder.dispatcher_sends.clear()
        self.coordinator = coordinator_module.TelegrafBridgeCoordinator(make_hass(), make_entry())

    async def test_cpu_message_updates_metric_and_fires_new_entity_signal(self):
        import json

        payload = json.dumps(
            {"fields": {"usage_idle": 80}, "tags": {"cpu": "cpu-total"}, "name": "cpu"}
        )
        await self.coordinator._async_process_message("systems/Tower/cpu", payload)

        self.assertIn(("tower", "cpu_usage"), self.coordinator.known_pairs)
        self.assertEqual(self.coordinator.metrics[("tower", "cpu_usage")].value, 20)
        self.assertTrue(self.coordinator.is_available("tower", "cpu_usage"))
        signals = [s[0] for s in recorder.dispatcher_sends]
        self.assertIn("telegraf_bridge_new_entity", signals)
        self.assertIn("telegraf_bridge_update_tower_cpu_usage", signals)

    async def test_second_message_for_known_pair_only_sends_update_signal(self):
        import json

        payload = json.dumps(
            {"fields": {"usage_idle": 80}, "tags": {"cpu": "cpu-total"}, "name": "cpu"}
        )
        await self.coordinator._async_process_message("systems/Tower/cpu", payload)
        recorder.dispatcher_sends.clear()
        await self.coordinator._async_process_message("systems/Tower/cpu", payload)

        signals = [s[0] for s in recorder.dispatcher_sends]
        self.assertNotIn("telegraf_bridge_new_entity", signals)
        self.assertIn("telegraf_bridge_update_tower_cpu_usage", signals)

    async def test_nvidia_smi_keys_metrics_by_gpu_index(self):
        import json

        gpu0 = json.dumps(
            {
                "fields": {"temperature_gpu": 30},
                "tags": {"index": "0", "name": "NVIDIA Foo"},
                "name": "nvidia_smi",
            }
        )
        gpu1 = json.dumps(
            {
                "fields": {"temperature_gpu": 40},
                "tags": {"index": "1", "name": "NVIDIA Bar"},
                "name": "nvidia_smi",
            }
        )
        await self.coordinator._async_process_message("systems/Tower/nvidia_smi", gpu0)
        self.assertIn(("tower", "gpu0_temp"), self.coordinator.known_pairs)

        await self.coordinator._async_process_message("systems/Tower/nvidia_smi", gpu1)
        self.assertIn(("tower", "gpu0_temp"), self.coordinator.known_pairs)
        self.assertIn(("tower", "gpu1_temp"), self.coordinator.known_pairs)


    async def test_dns_query_averages_after_window_fills(self):
        import json

        payload = json.dumps(
            {"fields": {"query_time_ms": 10.0}, "tags": {"server": "1.1.1.1"}, "name": "dns_query"}
        )
        for _ in range(4):
            await self.coordinator._async_process_message("systems/openwrt/dns_query", payload)
        self.assertNotIn(("openwrt", "dns_latency"), self.coordinator.known_pairs)

        await self.coordinator._async_process_message("systems/openwrt/dns_query", payload)
        self.assertIn(("openwrt", "dns_latency"), self.coordinator.known_pairs)
        self.assertEqual(self.coordinator.metrics[("openwrt", "dns_latency")].value, 10)

    async def test_net_rate_needs_two_samples(self):
        import json

        payload = json.dumps(
            {
                "fields": {"bytes_recv": 1_000_000, "bytes_sent": 500_000},
                "tags": {"interface": "eth0"},
                "name": "net",
            }
        )
        await self.coordinator._async_process_message("systems/openwrt/net", payload)
        self.assertNotIn(("openwrt", "wan_rx_mbps"), self.coordinator.known_pairs)

    async def test_short_topic_is_ignored(self):
        await self.coordinator._async_process_message("systems/Tower", "{}")
        self.assertEqual(self.coordinator.known_pairs, set())

    async def test_invalid_json_is_ignored(self):
        await self.coordinator._async_process_message("systems/Tower/cpu", "not json")
        self.assertEqual(self.coordinator.known_pairs, set())


class DeviceInfoTests(unittest.TestCase):
    def test_device_info_uses_raw_hostname(self):
        coordinator = coordinator_module.TelegrafBridgeCoordinator(make_hass(), make_entry())
        coordinator.hostnames["desktop_strix"] = "Desktop-STRIX"
        info = coordinator.device_info_for("desktop_strix")
        self.assertEqual(info["name"], "Desktop-STRIX")


if __name__ == "__main__":
    unittest.main()
