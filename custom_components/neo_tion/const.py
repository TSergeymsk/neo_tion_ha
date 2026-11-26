"""Constants for the Neo Tion integration."""

DOMAIN = "neo_tion"

PLATFORMS = ["climate", "sensor"]

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Увеличен интервал во избежание rate-limit от облака Tion
DEFAULT_SCAN_INTERVAL_SECONDS = 120