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

# openwrt's dns_query publishes one message per resolver, not a batch -
# average the last N samples per host into a single dns_latency reading.
DNS_QUERY_WINDOW_SIZE = 5

# Phase 7 parallel-validation: was appended to every entity's display name
# (and therefore its initially-generated entity_id) so it could run
# alongside the existing Node-RED/MQTT-discovery entities without
# colliding. Cutover (Phase 8, 2026-08-28) is done - Node-RED is disabled,
# its retained MQTT discovery configs cleared, and entity_ids renamed via a
# direct core.entity_registry edit to drop "_integration". Left at "" now;
# only needed if re-running a future parallel validation.
VALIDATION_NAME_SUFFIX = ""

