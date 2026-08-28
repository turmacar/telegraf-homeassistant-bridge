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

# telegraf publishes every 30s; mark an entity unavailable after 3 missed
# publishes and re-check on the same cadence.
STALE_AFTER_SECONDS = 90
STALENESS_CHECK_INTERVAL_SECONDS = 30

# dns_query publishes one message per resolver, not a batch - average the
# last N samples per host into a single dns_latency reading.
DNS_QUERY_WINDOW_SIZE = 5

# Optional suffix appended to every entity's display name (and therefore its
# initially-generated entity_id). Useful for running this integration
# alongside another MQTT-discovery-based setup without entity_id collisions
# while validating it side by side. Leave as "" for normal use.
VALIDATION_NAME_SUFFIX = ""

