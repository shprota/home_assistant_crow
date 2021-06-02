"""
Interfaces with Crow alarm control panel.
"""
import logging

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED, STATE_ALARM_ARMING,
    STATE_UNKNOWN)

from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_TRIGGER, SUPPORT_ALARM_ARM_CUSTOM_BYPASS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .consts import (DOMAIN)
import crow_security as crow


_LOGGER = logging.getLogger(__name__)


state_map = {
    'armed': STATE_ALARM_ARMED_AWAY,
    'arm in progress': STATE_ALARM_ARMING,
    'stay arm in progress': STATE_ALARM_ARMING,
    'stay_armed': STATE_ALARM_ARMED_HOME,
    'disarmed': STATE_ALARM_DISARMED,
}

set_state_map = {
    "ARMED_HOME": "stay",
    "ARMED_AWAY": "arm",
    "DISARM": "disarm",
}


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
):
    hub = hass.data[DOMAIN]
    alarms = []
    areas = await hub.panel.get_areas()
    alarms.extend([CrowAlarm(hub.panel, area) for area in areas])

    # hub.update_overview()
    async_add_entities(alarms)


class CrowAlarm(alarm.AlarmControlPanelEntity):
    """Representation of a Crow alarm status."""

    def __init__(self, panel: crow.Panel, area):
        """Initalize the Crow alarm panel."""
        self._panel = panel
        self._area = area
        self._state = state_map.get(self._area.get('state'), STATE_UNKNOWN)
        # self._digits = 4
        # self._changed_by = None

    @property
    def name(self):
        """Return the name of the device."""
        return '{} {}'.format(self._panel.name, self._area.get('name'))

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    # @property
    # def code_format(self):
    #     """Return the code format as regex."""
    #     return '^\\d{%s}$' % self._digits

    async def async_update(self):
        """Update alarm status."""
        _LOGGER.debug("Updating Crow area %s" % self._area.get('name'))
        self._area = await self._panel.get_area(self._area.get('id'))
        self._state = state_map.get(self._area.get('state'), STATE_UNKNOWN)
        if self._state == STATE_UNKNOWN:
            _LOGGER.error('Unknown alarm state %s', self._area.get('state'))

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self._async_set_arm_state('DISARMED', code)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        await self._async_set_arm_state('ARMED_HOME', code)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self._async_set_arm_state('ARMED_AWAY', code)

    async def async_alarm_trigger(self, code=None):
        pass

    async def async_alarm_arm_custom_bypass(self, code=None):
        pass

    def alarm_trigger(self, code=None):
        _LOGGER.info('Crow alarm trigger')
        pass

    async def _async_set_arm_state(self, state, code=None):
        """Send set arm state command."""
        _LOGGER.info('Crow set arm state %s', state)
        try:
            area = await self._panel.set_area_state(self._area.get('id'), set_state_map.get(state, "disarm"))
            if area:
                self._area = area
        except crow.crow.ResponseError as err:
            _LOGGER.error(err)
            if err.status_code != 408:
                raise err

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_CUSTOM_BYPASS | SUPPORT_ALARM_TRIGGER
