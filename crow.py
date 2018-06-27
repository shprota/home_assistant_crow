import logging

import voluptuous as vol

from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME,)
from datetime import timedelta
from homeassistant.helpers import discovery
from homeassistant.util import Throttle
# import homeassistant.config as conf_util
import homeassistant.helpers.config_validation as cv

ICSCP_DEVICE_TYPE_PIR = 0x31  # Infrared motion
ICSCP_DEVICE_TYPE_MAG = 0x32  # Magnetic contact
ICSCP_DEVICE_TYPE_RMT = 0x33  # Pendant remote control
ICSCP_DEVICE_TYPE_SMK = 0x34  # Smoke
ICSCP_DEVICE_TYPE_GAS = 0x35  # Gas
ICSCP_DEVICE_TYPE_GLB = 0x36  # Glass breakage
ICSCP_DEVICE_TYPE_CAM = 0x37  # Camera PIR
ICSCP_DEVICE_TYPE_FLD = 0x38  # Flood detector
ICSCP_DEVICE_TYPE_VIB = 0x39  # Vibration sensor
ICSCP_DEVICE_TYPE_HAM = 0x3A  # Home automation
ICSCP_DEVICE_TYPE_OEM = 0x3B  # OEM devices
ICSCP_DEVICE_TYPE_TFM = 0x3C  # TFM devices
ICSCP_DEVICE_TYPE_AIRQ = 0x3D  # OEM devices
ICSCP_DEVICE_TYPE_RADON = 0x3E  # RADON detector
ICSCP_DEVICE_TYPE_AIRPRES = 0x3F  # Air Pressure detector
ICSCP_DEVICE_TYPE_SRN = 0x45  # Siren
ICSCP_DEVICE_TYPE_SRN_SMART = 0x46  # Siren + Flash with config and commands
ICSCP_DEVICE_TYPE_OUT = 0x57  # Output (relay board)
ICSCP_DEVICE_TYPE_LED_KPD = 0x97  # LED (Icon) Keypad
ICSCP_DEVICE_TYPE_KPD = 0x98  # Keypad
ICSCP_DEVICE_TYPE_REPEATER = 0xB1  # repeater

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

    for component in ('alarm_control_panel', 'sensor'):
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
            # _LOGGER.info('Got zones: %s' % zones)
        except self._crow.Error as ex:
            _LOGGER.error('Crow operation failed, %s', ex)
            return False
        return True

    @Throttle(timedelta(seconds=30))
    def _get_measurements(self):
        m = self._panel.get_measurements()
        _LOGGER.debug("Get measurements: %s", m)
        return m

    def get_measurements(self):
        m = self._get_measurements()
        if not m and self._measurements:
            return self._measurements
        elif m:
            self._measurements = m
        return m

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




