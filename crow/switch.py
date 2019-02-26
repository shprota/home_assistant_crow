import logging
from time import time
from custom_components.crow.__init__ import HUB as hub
from homeassistant.components.switch import SwitchDevice
_LOGGER = logging.getLogger(__name__)


# noinspection PyUnusedLocal
def setup_platform(hass, config, add_devices, discovery_info=None):
    outputs = hub.get_outputs()
    switches = []
    switches.extend([
        CrowSmartplug(device)
        for device in outputs])
    add_devices(switches)


class CrowSmartplug(SwitchDevice):
    def __init__(self, device):
        """Initialize the Verisure device."""
        self._device_id = device.get('id')
        self._device_label = device.get('name', 'unknown')
        self._state = device.get('state', False)
        self._data = device
        self._change_timestamp = 0

    @property
    def name(self):
        """Return the name or location of the smartplug."""
        return self._device_label

    @property
    def is_on(self):
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._data is not None

    def turn_on(self, **kwargs):
        """Set smartplug status on."""
        hub.set_output_state(self._device_id, True)
        self._state = True
        self._change_timestamp = time()

    def turn_off(self, **kwargs):
        """Set smartplug status off."""
        hub.set_output_state(self._device_id, False)
        self._state = False
        self._change_timestamp = time()

    def update(self):
        self._data = hub.get_first(hub.get_outputs(), '$[?(@.id==%d)]', self._device_id)
        if time() - self._change_timestamp > 10:
            self._state = self._data.get('state', False)
