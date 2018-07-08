import logging

import voluptuous as vol

from homeassistant.const import (CONF_PASSWORD, CONF_USERNAME, EVENT_HOMEASSISTANT_STOP)
from datetime import timedelta
from homeassistant.helpers import discovery
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import Throttle
# import homeassistant.config as conf_util
import homeassistant.helpers.config_validation as cv

SIGNAL_CROW_UPDATE = "crow_update"
CONF_PANEL_MAC = 'panel_mac'

REQUIREMENTS = ['crow_security', 'jsonpath==0.75']

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
    import crow_security
    global HUB
    HUB = CrowHub(hass, config[DOMAIN], crow_security)
    if not HUB.login():
        return False
    hass.loop.create_task(HUB.ws_connect())

    for component in ('alarm_control_panel', 'sensor', 'switch', 'camera'):
        discovery.load_platform(hass, component, DOMAIN, {}, config)
    return True


class CrowHub(object):

    def __init__(self, hass, domain_config, crow):
        self._crow = crow
        import jsonpath
        self.jsonpath = jsonpath.jsonpath
        self.hass = hass
        self._mac = domain_config[CONF_PANEL_MAC]
        _LOGGER.info('Crow MAC: %s' % self._mac)
        self._panel = None
        self._zones = None
        self._outputs = None
        self._measurements = None
        self._pictures = None
        self.session = crow.Session(
            domain_config[CONF_USERNAME],
            domain_config[CONF_PASSWORD])
        self._ws_close_requested = False
        self.ws_reconnect_handle = None
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.ws_close())

    def login(self):
        try:
            self.session.login()
        except self._crow.Error as ex:
            _LOGGER.error('Could not log in to Crow, %s', ex)
            return False
        return True

    @Throttle(timedelta(seconds=60))
    def _get_zones(self):
        try:
            _LOGGER.info('Got panel: %s' % self.panel)
            zones = self.panel.get_zones()
            self._zones = zones
        except self._crow.Error as ex:
            _LOGGER.error('Crow operation failed, %s', ex)
            return False
        return True

    def get_zones(self):
        self._get_zones()
        return self._zones

    @Throttle(timedelta(seconds=120))
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

    # @Throttle(timedelta(seconds=120))
    def get_pictures(self, zone_id):
        return self.panel.get_pictures(zone_id)

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

    async def ws_connect(self):
        async def ws_cb(msg):
            _LOGGER.debug("Received message from Crow: %s", msg)
            async_dispatcher_send(self.hass, SIGNAL_CROW_UPDATE, msg)

        self._ws_close_requested = False
        try:
            ws_loop_future = self.session.ws_connect(self._mac, ws_cb)
        except self._crow.CrowLoginError as ex:
            _LOGGER.error("Authorization failed for websocket connection to Crow server: %s", ex)
            return
        except self._crow.CrowWsError as ex:
            _LOGGER.error("Could not subscribe to Crow websocket messages: %s", ex)
            return
        except Exception as ex:
            _LOGGER.error("Crow websocket error: %s", ex)
            if self.ws_reconnect_handle is None:
                _LOGGER.error("Error opening websocket connection: %s", ex)
                self.ws_reconnect_handle = async_track_time_interval(
                    self.hass, self.ws_connect, timedelta(minutes=2))
            return

        if self.ws_reconnect_handle is not None:
            self.ws_reconnect_handle()
            self.ws_reconnect_handle = None

        _LOGGER.info("Websocket connected")
        try:
            await ws_loop_future
        except Exception as err:
            _LOGGER.error(str(err))

        _LOGGER.info("Websocket closed")

        # If websocket was close was not requested, attempt to reconnect
        if not self._ws_close_requested:
            self.hass.loop.create_task(self.ws_connect())

    async def ws_close(self):
        self._ws_close_requested = True
        if self.ws_reconnect_handle is not None:
            self.ws_reconnect_handle()
            self.ws_reconnect_handle = None
        _LOGGER.info("Closing Crow Websocket")
        await self.session.ws_close()


