"""Constants for Strasbourg Piscines."""

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "strasbourg_piscines"
NAME: Final = "Strasbourg Piscines"
DATA_ATTRIBUTION: Final = "Données issues de l'Eurométropole de Strasbourg"
DATA_SOURCE_URL: Final = (
    "https://data.strasbourg.eu/explore/dataset/"
    "frequentation-en-temps-reel-des-piscines/"
)
API_URL: Final = (
    "https://data.strasbourg.eu/api/explore/v2.1/catalog/datasets/"
    "frequentation-en-temps-reel-des-piscines/records?limit=100"
)

CONF_POOLS: Final = "pools"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# The source is a live service; three minutes avoids needless duplicate polling.
DEFAULT_SCAN_INTERVAL_MINUTES: Final = 3
MIN_SCAN_INTERVAL_MINUTES: Final = 3
MAX_SCAN_INTERVAL_MINUTES: Final = 15
DEFAULT_UPDATE_INTERVAL: Final = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

PLATFORMS: Final = [Platform.SENSOR, Platform.BINARY_SENSOR]
