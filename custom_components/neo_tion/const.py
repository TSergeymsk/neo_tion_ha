"""Constants for the Neo Tion integration."""

DOMAIN = "neo_tion"

PLATFORMS = ["climate", "sensor"]

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL_SECONDS = 60

# Атрибуты, которые мы извлекаем из устройств Tion
ATTR_CO2 = "co2"
ATTR_TEMPERATURE = "temperature"
ATTR_HUMIDITY = "humidity"
ATTR_SPEED = "speed"
ATTR_IS_ON = "is_on"
ATTR_MODE = "mode"