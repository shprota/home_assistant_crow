"""
Interfaces with Crow sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.Crow/
"""
import logging
import copy

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS, PRESSURE_HPA, PERCENTAGE, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .consts import (DOMAIN)

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

iface_to_device_type = {
    INTERFACE_TEMPERATURE: 'temperature',
    INTERFACE_HUMIDITY: 'humidity',
    INTERFACE_AIR_PRESSURE: 'pressure',
    INTERFACE_GAS_VALUE: 'carbon_dioxide',
    INTERFACE_GAS_LEVEL: None,
}

iface_to_value_name = {
    INTERFACE_TEMPERATURE: 'temperature',
    INTERFACE_HUMIDITY: 'humidity',
    INTERFACE_AIR_PRESSURE: 'air_pressure',
    INTERFACE_GAS_VALUE: 'carbon_dioxide',
    INTERFACE_GAS_LEVEL: None,
}

# GAS Sensor IDT ZMOD 4410
# We have 5 levels of VOC (Volatile Organic Compounds)
GAS_LEVEL = {
    0: 'Clean',
    1: 'Good',
    2: 'Moderate',
    3: 'Bad',
    4: 'Very Bad',
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
        return PRESSURE_HPA
    elif iface == INTERFACE_TEMPERATURE:
        return TEMP_CELSIUS
    elif iface == INTERFACE_HUMIDITY:
        return PERCENTAGE
    elif iface == INTERFACE_GAS_LEVEL:
        return ''
    elif iface == INTERFACE_GAS_VALUE:
        return CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    return None


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
):
    hub = hass.data[DOMAIN]
    measurements = await hub.get_measurements()
    sensor_defs = []
    for sensor in hub.get(measurements, '$..values.*'):

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

    sensors = [CrowSensor(hub, sensor) for sensor in sensor_defs]

    async_add_entities(sensors)


class CrowSensor(Entity):
    """Representation of a Crow thermometer."""

    def __init__(self, hub, sensor):
        """Initialize the sensor."""
        _LOGGER.debug("Init crow sensor: %s", sensor)
        self._hub = hub
        self.value = None
        self._report_type = hub.get_first(sensor, '$._id.report_type')
        self._device_id = hub.get_first(sensor, '$._id.device_id')
        self._interface_type = hub.get_first(sensor, '$._id.dect_interface')
        # self._device_label = "{} - {}".format(sensor['name'], iface_labels.get(self._interface_type))
        self._device_label = sensor['name']
        self.value = get_iface_value(self._interface_type, sensor)
        self._attr_device_class = iface_to_device_type.get(self._interface_type)
        _LOGGER.info('Sensor[{}]: {}, {}'.format(sensor['name'], self._interface_type, self._device_label))

    @property
    def name(self):
        """Return the name of the device."""
        return self._device_label

    @property
    def unique_id(self):
        return self._device_id

    @property
    def state(self):
        """Return the state of the device."""
        return self.value

    @property
    def should_poll(self):
        return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.value is not None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return get_iface_unit(self._interface_type)

    def update_callback(self, msg):
        _LOGGER.debug('Got update for {}: '.format((self.name,)), msg)
        data = msg.get('data', {})
        if data:
            self.value = get_iface_value(self._interface_type, data)
            self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Subscribe to sensors events."""
        _LOGGER.debug('Added to hass: {}'.format((self.name,)))
        self._hub.subscribe(self._device_id, self.update_callback)

    # async def async_update(self):
    #     """Update the sensor."""
    #     _LOGGER.debug('Update called for {}'.format((self.name,)))
    #     measurements = await self._hub.get_measurements()
    #     data = self._hub.get_first(measurements,
    #                                '$.%d.values.[?(@._id.dect_interface==%d)]',
    #                                self._device_id, self._report_type)
    #     self.value = get_iface_value(self._interface_type, data)
