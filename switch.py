import logging
from time import time
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .consts import (DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
):
    hub = hass.data[DOMAIN]
    outputs = await hub.get_outputs()
    switches = []
    switches.extend([
        CrowSmartplug(hub, device)
        for device in outputs])

    # hub.update_overview()
    async_add_entities(switches)


class CrowSmartplug(SwitchEntity):
    def __init__(self, hub, device):
        """Initialize the Verisure device."""
        self._hub = hub
        self._device_id = device.get('id')
        self._device_label = device.get('name', 'unknown')
        self._state = device.get('state', False)
        self._data = device
        self._change_timestamp = 0

    @property
    def should_poll(self):
        return True

    @property
    def unique_id(self):
        return self._device_id

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

    async def async_turn_on(self, **kwargs):
        """Set smartplug status on."""
        await self._hub.set_output_state(self._device_id, True)
        self._state = True
        self._change_timestamp = time()

    async def async_turn_off(self, **kwargs):
        """Set smartplug status off."""
        await self._hub.set_output_state(self._device_id, False)
        self._state = False
        self._change_timestamp = time()

    async def async_update(self):
        outputs = await self._hub.get_outputs()
        self._data = self._hub.get_first(outputs, '$[?(@.id==%d)]', self._device_id)
        if time() - self._change_timestamp > 10:
            self._state = self._data.get('state', False)
