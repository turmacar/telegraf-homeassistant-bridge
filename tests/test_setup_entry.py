"""Unit tests for __init__.py's async_setup_entry/async_unload_entry,
stubbing homeassistant.* the same way the other test files do (no real HA
package installed - see repo memory telegraf-bridge-dev-workflow.md)."""

from __future__ import annotations

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
        # Always create a fresh module - see repo memory
        # telegraf-bridge-dev-workflow.md for why reusing sys.modules
        # entries across test files causes cross-file interference.
        module = types.ModuleType(module_name)
        _install_stub_module(stubbed_modules, module_name, module)
        if package:
            module.__path__ = []
        return module

    homeassistant = ensure_stub_module("homeassistant", package=True)
    components = ensure_stub_module("homeassistant.components", package=True)
    helpers = ensure_stub_module("homeassistant.helpers", package=True)

    mqtt_mod = ensure_stub_module("homeassistant.components.mqtt")
    config_entries_mod = ensure_stub_module("homeassistant.config_entries")
    const_mod = ensure_stub_module("homeassistant.const")
    core_mod = ensure_stub_module("homeassistant.core")
    device_registry_mod = ensure_stub_module("homeassistant.helpers.device_registry")
    dispatcher_mod = ensure_stub_module("homeassistant.helpers.dispatcher")
    event_mod = ensure_stub_module("homeassistant.helpers.event")
    storage_mod = ensure_stub_module("homeassistant.helpers.storage")

    recorder = types.SimpleNamespace(subscribe_calls=[], dispatcher_sends=[])

    async def async_subscribe(hass, topic, callback_fn, *a, **kw):
        recorder.subscribe_calls.append(topic)
        return lambda: None

    def async_dispatcher_send(hass, signal, *args) -> None:
        recorder.dispatcher_sends.append((signal, args))

    def async_track_time_interval(hass, action, interval):
        return lambda: None

    class DeviceInfo(dict):
        pass

    class ConfigEntry:
        def __init__(self, entry_id, data=None):
            self.entry_id = entry_id
            self.data = data or {}
            self.options = {}

    class HomeAssistant:
        pass

    class Platform:
        SENSOR = "sensor"

    mqtt_mod.async_subscribe = async_subscribe
    config_entries_mod.ConfigEntry = ConfigEntry
    const_mod.Platform = Platform
    core_mod.HomeAssistant = HomeAssistant
    core_mod.callback = lambda func: func
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


def load_modules(stubbed_modules: dict[str, object]):
    import importlib.util

    package_name = "telegraf_bridge"
    package_mod = types.ModuleType(package_name)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, package_name, package_mod)

    loaded = {}
    for submodule in ("const", "parsers", "coordinator", "__init__"):
        target_name = package_name if submodule == "__init__" else f"{package_name}.{submodule}"
        spec = importlib.util.spec_from_file_location(target_name, PACKAGE_ROOT / f"{submodule}.py")
        module = importlib.util.module_from_spec(spec)
        _install_stub_module(stubbed_modules, target_name, module)
        spec.loader.exec_module(module)
        loaded[submodule] = module
    return loaded


stubbed_modules: dict[str, object] = {}
recorder = install_homeassistant_stubs(stubbed_modules)
modules = load_modules(stubbed_modules)
init_module = modules["__init__"]
coordinator_module = modules["coordinator"]


def tearDownModule() -> None:
    restore_stubbed_modules(stubbed_modules)


def make_hass():
    return types.SimpleNamespace(
        data={},
        config_entries=types.SimpleNamespace(
            async_forward_entry_setups=_AsyncRecorder(),
            async_unload_platforms=_AsyncRecorder(return_value=True),
        ),
    )


class _AsyncRecorder:
    def __init__(self, return_value=None):
        self.calls = []
        self.return_value = return_value

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value


def make_entry(entry_id="entry-1"):
    return types.SimpleNamespace(entry_id=entry_id, data={}, options={})


class SetupEntryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        recorder.subscribe_calls.clear()
        recorder.dispatcher_sends.clear()

    async def test_setup_entry_creates_coordinator_and_forwards_platforms(self):
        hass = make_hass()
        entry = make_entry()

        result = await init_module.async_setup_entry(hass, entry)

        self.assertTrue(result)
        coordinator = hass.data[init_module.DOMAIN][entry.entry_id]
        self.assertIsInstance(coordinator, coordinator_module.TelegrafBridgeCoordinator)
        self.assertEqual(len(hass.config_entries.async_forward_entry_setups.calls), 1)
        self.assertEqual(recorder.subscribe_calls, ["systems/#"])

    async def test_unload_entry_removes_coordinator_and_unsubscribes(self):
        hass = make_hass()
        entry = make_entry()
        await init_module.async_setup_entry(hass, entry)

        result = await init_module.async_unload_entry(hass, entry)

        self.assertTrue(result)
        self.assertNotIn(entry.entry_id, hass.data[init_module.DOMAIN])

    async def test_unload_entry_keeps_coordinator_if_platform_unload_fails(self):
        hass = make_hass()
        hass.config_entries.async_unload_platforms = _AsyncRecorder(return_value=False)
        entry = make_entry()
        await init_module.async_setup_entry(hass, entry)

        result = await init_module.async_unload_entry(hass, entry)

        self.assertFalse(result)
        self.assertIn(entry.entry_id, hass.data[init_module.DOMAIN])


if __name__ == "__main__":
    unittest.main()
