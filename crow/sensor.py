"""
Interfaces with Crow sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.Crow/
"""
import logging
import copy

from custom_components.crow import HUB as hub
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)


INTERFACE_TEMPERATURE = 32533
INTERFACE_HUMIDITY = 32532
INTERFACE_AIR_PRESSURE = 32535
INTERFACE_GAS_LEVEL = 61
INTERFACE_GAS_VALUE = 62  # Fake virtual dect_interface number


iface_labels = {
    INTERFACE_TEMPERATURE: 'Temperature',
    INTERFACE_HUMIDITY: 'Humidity',
    INTERFACE_AIR_PRESSURE: 'Air Pressure',
    INTERFACE_GAS_VALUE: 'Gas Value',
    INTERFACE_GAS_LEVEL: 'Gas Level',
}

# GAS Sensor IDT ZMOD 4410
# We have 5 levels of VOC (Volatile Organic Compounds)
GAS_LEVEL = {
    0 : 'Clean',
    1 : 'Good',
    2 : 'Moderate',
    3 : 'Bad',
    4 : 'Very Bad',
}


def get_iface_value(iface, data):
    if data is None:
        return None
    if iface == INTERFACE_AIR_PRESSURE:
        return data['air_pressure']
    elif iface == INTERFACE_TEMPERATURE:
        return round(data['temperature'] / 10) / 10
    elif iface == INTERFACE_HUMIDITY:
        return round(data['humidity'] / 10) / 10
    elif iface == INTERFACE_GAS_VALUE:
        return data['gas_value']
    elif iface == INTERFACE_GAS_LEVEL:
        return GAS_LEVEL.get(data['gas_level'])
    return None


def get_iface_unit(iface):
    if iface == INTERFACE_AIR_PRESSURE:
        return 'hPa'
    elif iface == INTERFACE_TEMPERATURE:
        return TEMP_CELSIUS
    elif iface == INTERFACE_HUMIDITY:
        return '%'
    elif iface == INTERFACE_GAS_LEVEL:
        return ''
    elif iface == INTERFACE_GAS_VALUE:
        return 'mg/m3'
    return None


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Crow platform."""
    measurements = hub.get_measurements()
    _LOGGER.debug("Setup crow sensors: %s", measurements)

    sensor_defs = []
    for sensor in hub.get(measurements, '$..values.*'):
        # workaround for AIRQ report cause it is all in one message
        # (no separate value for each type of data), so we multiply sensor few times
        if sensor['_id']['dect_interface'] == INTERFACE_GAS_LEVEL:
            for dect_interface in (INTERFACE_TEMPERATURE, INTERFACE_HUMIDITY,
                INTERFACE_AIR_PRESSURE, INTERFACE_GAS_LEVEL, INTERFACE_GAS_VALUE):
                s = copy.deepcopy(sensor)
                s['name'] = measurements.get(str(hub.get_first(sensor, '$._id.device_id'))).get('name')
                s['_id']['dect_interface'] = dect_interface
                sensor_defs.append(s)
        else:
            sensor['name'] = measurements.get(str(hub.get_first(sensor, '$._id.device_id'))).get('name')
            sensor_defs.append(sensor)

    sensors = [CrowSensor(sensor) for sensor in sensor_defs]

    add_devices(sensors)


class CrowSensor(Entity):
    """Representation of a Crow thermometer."""

    def __init__(self, sensor):
        """Initialize the sensor."""
        _LOGGER.debug("Init crow sensor: %s", sensor)
        self.value = None
        self._report_type = hub.get_first(sensor, '$._id.report_type')
        self._device_id = hub.get_first(sensor, '$._id.device_id')
        self._interface_type = hub.get_first(sensor, '$._id.dect_interface')
        self._device_label = "{} - {}".format(sensor['name'], iface_labels.get(self._interface_type))
        self.value = get_iface_value(self._interface_type, sensor)
        _LOGGER.warning('Sensor[{}]: {}, {}'.format(sensor['name'], self._interface_type, self._device_label))


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
                             self._device_id, self._report_type)
        self.value = get_iface_value(self._interface_type, data)
