import errno
import logging
import os

from crow_security import ResponseError

from homeassistant.components.camera import Camera
from homeassistant.components.verisure.const import SERVICE_CAPTURE_SMARTCAM
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
from .consts import (DOMAIN)

# from custom_components.crow import CONF_SMARTCAM

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
):
    directory_path = hass.config.config_dir
    if not os.access(directory_path, os.R_OK):
        _LOGGER.error("file path %s is not readable", directory_path)
        return False

    hub = hass.data[DOMAIN]
    zones = await hub.panel.get_zones()
    zones = filter(lambda d: d.get('type') == 55, zones)
    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_CAPTURE_SMARTCAM,
        {},
        "async_capture_smartcam",
    )
    smartcams = []
    for device in zones:
        smartcams.append(CrowSmartcam(hub, device, directory_path))
    async_add_entities(smartcams)


class CrowSmartcam(Camera):
    """Representation of a Crow camera."""

    def __init__(self, hub, device, directory_path):
        """Initialize Crow File Camera component."""
        super().__init__()
        self._hub = hub
        self._device = device
        self._device_label = device.get('name', 'unknown')
        self._directory_path = directory_path
        self._image_file = None
        self._image = None
        self.is_streaming = False

#        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP,
#                             self.delete_image)

    async def async_added_to_hass(self):
        """Subscribe to sensors events."""
        # async_dispatcher_connect(self.hass, SIGNAL_CROW_UPDATE, self.async_update_callback)
        await self.check_imagelist()

    @callback
    async def async_update_callback(self, msg):
        if msg.get('type') != 'event' and msg.get('data', {}).get('cid') != 5200:
            return
        await self.check_imagelist()

    async def async_camera_image(self):
        """Return image response."""
        await self.check_imagelist()
        if not self._image_file:
            # _LOGGER.debug("No image to display")
            return
        with open(self._image_file, 'rb') as file:
            return file.read()

    async def check_imagelist(self):
        """Check the contents of the image list."""
        images = await self._hub.panel.get_pictures(self._device.get('id'))
        if not images:
            return
        new_image = images[0]
        _LOGGER.debug("Image: %s", new_image)
        new_id = new_image.get('id', -1)
        if new_id == -1 or (self._image and self._image.get('id') == new_image.get('id')):
            _LOGGER.debug("The image is the same, or loading image_id")
            return
        _LOGGER.debug("Download new image %s", new_id)
        new_image_path = os.path.join(
            self._directory_path, '{}{}'.format(new_id, '.jpg'))
        await self._hub.session.download_picture(new_image, new_image_path)
        self.delete_image(self)

        self._image = new_image
        self._image_file = new_image_path

    def delete_image(self, event):
        """Delete an old image."""
        if not self._image:
            return
        remove_image = os.path.join(
            self._directory_path, '{}{}'.format(self._image.get('id'), '.jpg'))
        try:
            os.remove(remove_image)
            _LOGGER.debug("Deleting old image %s", remove_image)
        except OSError as error:
            if error.errno != errno.ENOENT:
                raise

    async def async_capture_smartcam(self) -> None:
        """Capture a new picture from a smartcam."""
        try:
            _LOGGER.debug("Capturing new image from %s", self._device.get('id'))
            resp = await self._hub.capture_cam_image(self._device.get('id'))
            _LOGGER.debug("Capture Response: %s", resp)
        except ResponseError as ex:
            _LOGGER.error("Could not capture image, %s", ex)

    @property
    def name(self):
        """Return the name of this camera."""
        return self._device.get('name')

    @property
    def unique_id(self):
        return '{}-{}'.format(self._hub.panel.mac, self._device.get('id'))
