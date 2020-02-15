"""
Interfaces with Crow sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.Crow/
"""
import logging

from custom_components.crow import HUB as hub
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

INTERFACE_TEMPERATURE = 32533
INTERFACE_HUMIDITY = 32532
INTERFACE_AIR_PRESSURE = 32535

iface_labels = {
    INTERFACE_TEMPERATURE: 'Temperature',
    INTERFACE_HUMIDITY: 'Humidity',
    INTERFACE_AIR_PRESSURE: 'Air Pressure'
}


def get_iface_value(iface, data):
    if iface == INTERFACE_AIR_PRESSURE:
        return data['air_pressure']
    if iface == INTERFACE_TEMPERATURE:
        return round(data['temperature'] / 10) / 10
    if iface == INTERFACE_HUMIDITY:
        return round(data['humidity'] / 10) / 10
    return None


def get_iface_unit(iface):
    if iface == INTERFACE_AIR_PRESSURE:
        return 'hPa'
    if iface == INTERFACE_TEMPERATURE:
        return TEMP_CELSIUS
    if iface == INTERFACE_HUMIDITY:
        return '%'
    return None


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Crow platform."""
    sensors = []
    measurements = hub.get_measurements()
    _LOGGER.debug("Setup crow sensors: %s", measurements)

    sensor_defs = hub.get(measurements, '$..values.*')
    for sensor in sensor_defs:
        sensor['name'] = measurements.get(str(hub.get_first(sensor, '$._id.device_id'))).get('name')

    sensors.extend([CrowSensor(sensor) for sensor in sensor_defs])

    add_devices(sensors)


class CrowSensor(Entity):
    """Representation of a Crow thermometer."""

    def __init__(self, sensor):
        """Initialize the sensor."""
        _LOGGER.debug("Init crow sensor: %s", sensor)
        self.value = None
        self._device_id = hub.get_first(sensor, '$._id.device_id')
        self._interface_type = hub.get_first(sensor, '$._id.dect_interface')
        self._device_label = "{} - {}".format(sensor['name'], iface_labels.get(self._interface_type))
        self.value = get_iface_value(self._interface_type, sensor)


    @property
    def name(self):
        """Return the name of the device."""
        return self._device_label

    @property
    def state(self):
        """Return the state of the device."""
        return self.value

    @property
    def available(self):
        """Return True if entity is available."""
        return self.value is not None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return get_iface_unit(self._interface_type)

    # pylint: disable=no-self-use
    def update(self):
        """Update the sensor."""
        data = hub.get_first(hub.get_measurements(),
                             '$.%d.values.[?(@._id.dect_interface==%d)]',
                             self._device_id, self._interface_type)
        self.value = get_iface_value(self._interface_type, data)

