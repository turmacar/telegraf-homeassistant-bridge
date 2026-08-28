# Telegraf Bridge

Home Assistant custom integration that auto-discovers hosts publishing
[telegraf](https://github.com/influxdata/telegraf) metrics to `systems/#` over
MQTT and creates native sensor entities for them.

## Requirements

- Home Assistant's core `mqtt` integration must already be configured.
- Hosts publishing telegraf metrics to `systems/{hostname}/{measurement}`.

## Installation

Via HACS (custom repository) or by copying
`custom_components/telegraf_bridge/` into your `config/custom_components/`
directory, then restart Home Assistant and add the integration via
Settings -> Devices & Services.
