import logging

import voluptuous as vol

from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME,)
from datetime import timedelta
from homeassistant.helpers import discovery
from homeassistant.util import Throttle
# import homeassistant.config as conf_util
import homeassistant.helpers.config_validation as cv

CONF_PANEL_MAC = 'panel_mac'

REQUIREMENTS = ['crow', 'jsonpath==0.75']

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'crow'

HUB = None

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PANEL_MAC): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    import crow
    global HUB
    HUB = CrowHub(config[DOMAIN], crow)
    if not HUB.login():
        return False

    # if not HUB.get_devices():
    #     return False

    for component in ('alarm_control_panel', 'sensor', 'switch'):
        discovery.load_platform(hass, component, DOMAIN, {}, config)
    return True


class CrowHub(object):

    def __init__(self, domain_config, crow):
        self._crow = crow
        import jsonpath
        self.jsonpath = jsonpath.jsonpath
        self._mac = domain_config[CONF_PANEL_MAC]
        _LOGGER.info('Crow MAC: %s' % self._mac)
        self._panel = None
        self._devices = None
        self._outputs = None
        self._measurements = None
        self.session = crow.Session(
            domain_config[CONF_USERNAME],
            domain_config[CONF_PASSWORD])

    def login(self):
        try:
            self.session.login()
        except self._crow.Error as ex:
            _LOGGER.error('Could not log in to Crow, %s', ex)
            return False
        return True

    @Throttle(timedelta(seconds=60))
    def get_devices(self):
        try:
            _LOGGER.info('Got panel: %s' % self.panel)
            zones = self.panel.get_zones()
            self._devices = zones
        except self._crow.Error as ex:
            _LOGGER.error('Crow operation failed, %s', ex)
            return False
        return True

    @Throttle(timedelta(seconds=30))
    def _get_measurements(self):
        m = self.panel.get_measurements()
        return m

    def get_measurements(self):
        m = self._get_measurements()
        if not m and self._measurements:
            return self._measurements
        elif m:
            self._measurements = m
        return m

    @Throttle(timedelta(seconds=30))
    def _get_outputs(self):
        o = self.panel.get_outputs()
        return o

    def get_outputs(self):
        o = self._get_outputs()
        if not o and self._outputs:
            return self._outputs
        elif o:
            self._outputs = o
        return o

    def set_output_state(self, output_id, state):
        return self._panel.set_output_state(output_id, state)

    @property
    def panel(self):
        if not self._panel:
            self._panel = self.session.get_panel(self._mac)
        return self._panel

    def get(self, obj, jpath, *args):
        """Get values from the overview that matches the jsonpath."""
        res = self.jsonpath(obj, jpath % args)
        return res if res else []

    def get_first(self, obj, jpath, *args):
        """Get first value from the overview that matches the jsonpath."""
        res = self.get(obj, jpath, *args)
        return res[0] if res else None
