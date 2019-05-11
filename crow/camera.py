import errno
import logging
import os

from homeassistant.components.camera import Camera
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..crow import HUB as hub, SIGNAL_CROW_UPDATE

# from custom_components.crow import CONF_SMARTCAM

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Crow Camera."""
    # if not int(hub.config.get(CONF_SMARTCAM, 1)):
    #     return False
    directory_path = hass.config.config_dir
    if not os.access(directory_path, os.R_OK):
        _LOGGER.error("file path %s is not readable", directory_path)
        return False

    zones = hub.get_zones()
    zones = filter(lambda d: d.get('type') == 55, zones)
    smartcams = []
    smartcams.extend([
        CrowSmartcam(hass, device, directory_path)
        for device in zones])
    add_devices(smartcams)


class CrowSmartcam(Camera):
    """Representation of a Verisure camera."""

    def __init__(self, hass, device, directory_path):
        """Initialize Verisure File Camera component."""
        super().__init__()
        self._device = device
        self._device_label = device.get('name', 'unknown')
        self._directory_path = directory_path
        self._image_file = None
        self._image = None
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP,
                             self.delete_image)

    async def async_added_to_hass(self):
        """Subscribe to sensors events."""
        async_dispatcher_connect(self.hass, SIGNAL_CROW_UPDATE, self.async_update_callback)
        self.check_imagelist()

    @callback
    def async_update_callback(self, msg):
        if msg.get('type') != 'event' and msg.get('data', {}).get('cid') != 5200:
            return
        self.check_imagelist()

    def camera_image(self):
        """Return image response."""
        # self.check_imagelist()
        if not self._image_file:
            _LOGGER.debug("No image to display")
            return
        _LOGGER.debug("Trying to open %s", self._image_file)
        with open(self._image_file, 'rb') as file:
            return file.read()

    def check_imagelist(self):
        """Check the contents of the image list."""
        images = hub.get_pictures(self._device.get('id'))
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
        hub.session.download_picture(new_image, new_image_path)
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

    @property
    def name(self):
        """Return the name of this camera."""
        return self._device.get('name')
