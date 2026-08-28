# Telegraf Bridge

Auto-discovers hosts publishing [telegraf](https://github.com/influxdata/telegraf)
metrics to `systems/#` over MQTT and creates native Home Assistant sensor
entities for them.

## Features

- Zero-config host onboarding - new hosts show up automatically as soon as
  telegraf starts publishing for them
- Native `SensorEntity` objects
- Per-host manufacturer/model/display name overrides via an Options Flow
- Entities persist across Home Assistant restarts and reappear immediately
  (as unavailable) before the first message, without waiting on telegraf

## Requirements

- Home Assistant's core `mqtt` integration must already be configured
- Hosts publishing telegraf metrics to `systems/{hostname}/{measurement}`
