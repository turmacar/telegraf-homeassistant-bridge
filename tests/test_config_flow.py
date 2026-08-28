"""Unit tests for config_flow.py, stubbing homeassistant.config_entries/core
the same way test_coordinator.py stubs the rest of homeassistant.* (no real
HA package installed anywhere on this machine - see repo memory
telegraf-bridge-dev-workflow.md). Uses the REAL `voluptuous` package since
it's a standalone validation library with no HA dependency."""

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


class FakeConfigFlowResult(dict):
    """Just a dict - HA's flow results are plain dicts under the hood."""


class FakeFlowBase:
    """Shared behavior for the stub ConfigFlow/OptionsFlow base classes."""

    def async_show_form(self, *, step_id, data_schema=None, errors=None):
        return FakeConfigFlowResult(
            type="form", step_id=step_id, data_schema=data_schema, errors=errors or {}
        )

    def async_create_entry(self, *, title, data):
        return FakeConfigFlowResult(type="create_entry", title=title, data=data)

    def async_abort(self, *, reason):
        return FakeConfigFlowResult(type="abort", reason=reason)


def install_homeassistant_stubs(stubbed_modules: dict[str, object]) -> None:
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

    ensure_stub_module("homeassistant", package=True)
    config_entries_mod = ensure_stub_module("homeassistant.config_entries")
    core_mod = ensure_stub_module("homeassistant.core")

    class ConfigFlow(FakeFlowBase):
        def __init_subclass__(cls, *, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls.domain = domain

        async def async_set_unique_id(self, unique_id):
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            return None

    class OptionsFlow(FakeFlowBase):
        pass

    class ConfigEntry:
        def __init__(self, entry_id, data=None, options=None):
            self.entry_id = entry_id
            self.data = data or {}
            self.options = options or {}

    config_entries_mod.ConfigFlow = ConfigFlow
    config_entries_mod.OptionsFlow = OptionsFlow
    config_entries_mod.ConfigEntry = ConfigEntry
    core_mod.callback = lambda func: func


def load_config_flow_module(stubbed_modules: dict[str, object]):
    import importlib.util

    package_name = "telegraf_bridge"
    package_mod = types.ModuleType(package_name)
    package_mod.__path__ = [str(PACKAGE_ROOT)]
    _install_stub_module(stubbed_modules, package_name, package_mod)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.const", PACKAGE_ROOT / "const.py"
    )
    const_module = importlib.util.module_from_spec(spec)
    _install_stub_module(stubbed_modules, f"{package_name}.const", const_module)
    spec.loader.exec_module(const_module)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.config_flow", PACKAGE_ROOT / "config_flow.py"
    )
    module = importlib.util.module_from_spec(spec)
    _install_stub_module(stubbed_modules, f"{package_name}.config_flow", module)
    spec.loader.exec_module(module)
    return module


stubbed_modules: dict[str, object] = {}
install_homeassistant_stubs(stubbed_modules)
config_flow_module = load_config_flow_module(stubbed_modules)


def tearDownModule() -> None:
    restore_stubbed_modules(stubbed_modules)


def make_flow(hass, entries=()):
    flow = config_flow_module.TelegrafBridgeConfigFlow()
    flow.hass = types.SimpleNamespace(
        config_entries=types.SimpleNamespace(async_entries=lambda domain: list(entries))
    )
    return flow


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_aborts_when_mqtt_not_configured(self):
        flow = make_flow(None, entries=[])
        result = await flow.async_step_user()
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["reason"], "mqtt_not_configured")

    async def test_shows_form_when_mqtt_configured(self):
        flow = make_flow(None, entries=["mqtt-entry"])
        result = await flow.async_step_user()
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "user")

    async def test_creates_entry_with_submitted_topic(self):
        flow = make_flow(None, entries=["mqtt-entry"])
        result = await flow.async_step_user({"topic": "systems/#"})
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"], {"topic": "systems/#"})


class OptionsFlowTests(unittest.IsolatedAsyncioTestCase):
    def _make_options_flow(self, known_pairs=(), options=None):
        entry = types.SimpleNamespace(entry_id="entry-1", options=options or {})
        flow = config_flow_module.TelegrafBridgeOptionsFlow(entry)
        coordinator = types.SimpleNamespace(known_pairs=set(known_pairs))
        flow.hass = types.SimpleNamespace(data={config_flow_module.DOMAIN: {"entry-1": coordinator}})
        return flow

    async def test_aborts_when_no_hosts_discovered(self):
        flow = self._make_options_flow(known_pairs=set())
        result = await flow.async_step_init()
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["reason"], "no_hosts_discovered")

    async def test_init_lists_discovered_hosts(self):
        flow = self._make_options_flow(known_pairs={("server", "cpu_usage"), ("raspberrypi2", "cpu_temp")})
        result = await flow.async_step_init()
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "init")

    async def test_selecting_host_advances_to_host_step(self):
        flow = self._make_options_flow(known_pairs={("server", "cpu_usage")})
        result = await flow.async_step_init({"host": "server"})
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "host")
        self.assertEqual(flow._selected_host, "server")

    async def test_submitting_host_overrides_saves_options(self):
        flow = self._make_options_flow(known_pairs={("server", "cpu_usage")})
        flow._selected_host = "server"
        result = await flow.async_step_host(
            {"manufacturer": "Unraid", "model": "Server", "name": ""}
        )
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            result["data"]["host_overrides"]["server"],
            {"manufacturer": "Unraid", "model": "Server"},
        )

    async def test_blank_fields_are_not_saved(self):
        flow = self._make_options_flow(known_pairs={("server", "cpu_usage")})
        flow._selected_host = "server"
        result = await flow.async_step_host({"manufacturer": "", "model": "", "name": ""})
        self.assertEqual(result["data"]["host_overrides"]["server"], {})

    async def test_existing_overrides_prefill_the_form(self):
        flow = self._make_options_flow(
            known_pairs={("server", "cpu_usage")},
            options={"host_overrides": {"server": {"manufacturer": "Unraid"}}},
        )
        flow._selected_host = "server"
        result = await flow.async_step_host()
        self.assertEqual(result["type"], "form")


if __name__ == "__main__":
    unittest.main()
