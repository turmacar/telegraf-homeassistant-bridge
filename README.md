# Telegraf Bridge

Home Assistant custom integration that auto-discovers hosts publishing
[telegraf](https://github.com/influxdata/telegraf) metrics to `systems/#` over
MQTT and creates native sensor entities for them.

## Requirements

- Home Assistant's core `mqtt` integration must already be configured.
- Hosts publishing telegraf metrics to `systems/{hostname}/{measurement}`.

## Installation

### HACS (custom repository)

**Note**: this repo is currently **private**. [HACS only works reliably with
public repositories](https://hacs.xyz/docs/publish/start/) - custom-repository
install and the `hacs/action` CI validation won't fully work until it's made
public. The packaging is otherwise ready to go (`hacs.json`, `info.md`,
GitHub topics, `v0.1.0` release) - flipping the repo to public is the only
remaining step. Once public:

1. HACS -> Integrations -> top-right menu (⋮) -> **Custom repositories**
2. Repository: `https://github.com/turmacar/telegraf-homeassistant-bridge`,
   Category: **Integration**
3. Install "Telegraf Bridge" from HACS, then restart Home Assistant
4. Settings -> Devices & Services -> Add Integration -> **Telegraf Bridge**

### Manual

Copy `custom_components/telegraf_bridge/` into your `config/custom_components/`
directory, then restart Home Assistant and add the integration via
Settings -> Devices & Services.
