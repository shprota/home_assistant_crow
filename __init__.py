import logging

import voluptuous as vol

from .consts import (CONF_PANEL_MAC, DOMAIN)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .hub import CrowHub
from homeassistant.const import (CONF_PASSWORD, CONF_EMAIL,)
import homeassistant.helpers.config_validation as cv
from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
)
# from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN


REQUIREMENTS = ['crow_security', 'jsonpath==0.75']

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PANEL_MAC): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [
    ALARM_CONTROL_PANEL_DOMAIN,
    # BINARY_SENSOR_DOMAIN,
    SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    # CAMERA_DOMAIN,
]


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry):
    crow_hub = CrowHub(config.data, hass)
    await crow_hub.init_panel()
    hass.data[DOMAIN] = crow_hub
    hass.config_entries.async_setup_platforms(config, PLATFORMS)
    hass.loop.create_task(crow_hub.ws_connect())
    return True
