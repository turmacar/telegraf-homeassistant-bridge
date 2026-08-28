"""Constants for the Telegraf Bridge integration."""

from __future__ import annotations

DOMAIN = "telegraf_bridge"

# Wildcard MQTT topic telegraf publishes to: systems/{hostname}/{measurement}
DEFAULT_TOPIC = "systems/#"
CONF_TOPIC = "topic"

# Dispatcher signal fired when a new (host_id, metric) pair is first seen.
SIGNAL_NEW_ENTITY = f"{DOMAIN}_new_entity"

# Storage version/key for the persisted set of known (host_id, metric) pairs.
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN
