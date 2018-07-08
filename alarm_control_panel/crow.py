"""
Interfaces with Crow alarm control panel.
"""
import logging
from time import sleep

import homeassistant.components.alarm_control_panel as alarm
from custom_components.crow import HUB as hub
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY, STATE_ALARM_ARMED_HOME, STATE_ALARM_DISARMED, STATE_ALARM_ARMING,
    STATE_UNKNOWN)

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


def setup_platform(hass, config, add_devices, discovery_info=None):
    alarms = []
    areas = hub.panel.get_areas()
    alarms.extend([CrowAlarm(area) for area in areas])

    # hub.update_overview()
    add_devices(alarms)


class CrowAlarm(alarm.AlarmControlPanel):
    """Representation of a Crow alarm status."""

    def __init__(self, area):
        """Initalize the Crow alarm panel."""
        self._area = area
        self._state = state_map.get(self._area.get('state'), STATE_UNKNOWN)
        # self._digits = 4
        # self._changed_by = None

    @property
    def name(self):
        """Return the name of the device."""
        return '{} {}'.format(hub.panel.name, self._area.get('name'))

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    # @property
    # def code_format(self):
    #     """Return the code format as regex."""
    #     return '^\\d{%s}$' % self._digits

    def update(self):
        """Update alarm status."""
        # _LOGGER.debug("Updating Crow area %s" % self._area.get('name'))
        self._area = hub.panel.get_area(self._area.get('id'))
        self._state = state_map.get(self._area.get('state'), STATE_UNKNOWN)
        if self._state == STATE_UNKNOWN:
            _LOGGER.error('Unknown alarm state %s', self._area.get('state'))

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._set_arm_state('DISARMED', code)

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._set_arm_state('ARMED_HOME', code)

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._set_arm_state('ARMED_AWAY', code)

    def alarm_trigger(self, code=None):
        _LOGGER.info('Crow alarm trigger')
        pass

    def alarm_arm_custom_bypass(self, code=None):
        _LOGGER.info('Crow alarm bypass')

    def _set_arm_state(self, state, code=None):
        """Send set arm state command."""
        _LOGGER.info('Crow set arm state %s', state)
        area = hub.panel.set_area_state(self._area.get('id'), set_state_map.get(state, "disarm"))
        if area:
            self._area = area
