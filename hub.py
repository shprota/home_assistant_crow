import logging
from datetime import timedelta
from typing import Callable

from crow_security import Panel

from homeassistant.const import (CONF_PASSWORD, CONF_EMAIL,)
from .consts import (CONF_PANEL_MAC, DOMAIN)
import crow_security as crow

from homeassistant.util import Throttle

_LOGGER = logging.getLogger(DOMAIN)


class CrowHub(object):

    def __init__(self, domain_config, hass):
        self._crow = crow
        self._hass = hass
        # noinspection PyPackageRequirements
        import jsonpath
        self.jsonpath = jsonpath.jsonpath
        self._mac = domain_config[CONF_PANEL_MAC]
        _LOGGER.info('Crow MAC: %s' % self._mac)
        # noinspection PyTypeChecker
        self._panel: Panel = None
        self._devices = None
        self._outputs = None
        self._measurements = None
        self._subscriptions = {}
        self.session = crow.Session(
            domain_config[CONF_EMAIL],
            domain_config[CONF_PASSWORD])

    @property
    def mac(self):
        return self._mac

    async def init_panel(self):
        self._panel = await self.session.get_panel(self._mac)

    @Throttle(timedelta(seconds=60))
    async def get_devices(self):
        try:
            _LOGGER.info('Got panel: %s' % self.panel)
            zones = await self.panel.get_zones()
            self._devices = zones
        except self._crow.Error as ex:
            _LOGGER.error('Crow operation failed, %s', ex)
            return False
        return True

    @Throttle(timedelta(seconds=30))
    async def _get_measurements(self):
        m = await self.panel.get_measurements()
        return m

    async def get_measurements(self):
        m = await self._get_measurements()
        if not m and self._measurements:
            return self._measurements
        elif m:
            self._measurements = m
        return m

    @Throttle(timedelta(seconds=30))
    async def _get_outputs(self):
        o = await self.panel.get_outputs()
        return o

    async def get_outputs(self):
        o = await self._get_outputs()
        if not o and self._outputs:
            return self._outputs
        elif o:
            self._outputs = o
        return o

    def set_output_state(self, output_id, state):
        return self._panel.set_output_state(output_id, state)

    def capture_cam_image(self, zone_id):
        return self._panel.capture_cam_image(zone_id)

    @property
    def panel(self):
        return self._panel

    def get(self, obj, jpath, *args):
        """Get values from the overview that matches the jsonpath."""
        res = self.jsonpath(obj, jpath % args)
        return res if res else []

    def get_first(self, obj, jpath, *args):
        """Get first value from the overview that matches the jsonpath."""
        res = self.get(obj, jpath, *args)
        return res[0] if res else None

    def subscribe(self, device_id, callback: Callable):
        self._subscriptions[device_id] = callback

    def ws_connect(self):
        async def ws_cb(msg):
            if msg.get('type') == 'info' and msg.get('data', {}).get('_id', {}).get('dect_interface') == 32768:
                _LOGGER.debug("Not processed message: %s", msg)
                return
            _LOGGER.debug("Received message from Crow: %s", msg)
            device_id = msg.get('data', {}).get('_id', {}).get('device_id')
            callback = self._subscriptions.get(device_id)
            if callback is not None:
                callback(msg)

        return self.session.ws_connect(self._mac, ws_cb)
