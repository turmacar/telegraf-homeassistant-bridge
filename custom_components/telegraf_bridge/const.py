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

# Phase 7 parallel-validation: appended to every entity's display name (and
# therefore its initially-generated entity_id) so it can run alongside the
# existing Node-RED/MQTT-discovery entities without colliding. unique_id is
# deliberately NOT suffixed, so removing this at Phase 8 cutover renames the
# same entities in place rather than creating new ones - but note entity_id
# itself is sticky once created (see repo memory
# ha-mqtt-discovery-entity-id.md), so cutover also needs an explicit
# entity_registry rename pass to drop "_integration" from entity_id, not
# just clearing this constant.
VALIDATION_NAME_SUFFIX = " (Integration)"

