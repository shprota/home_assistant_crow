import logging

from .consts import DOMAIN, CONF_PANEL_MAC
from homeassistant import config_entries, core, exceptions
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (CONF_PASSWORD, CONF_EMAIL,)
import voluptuous as vol
import homeassistant.helpers.config_validation as cv


_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_PANEL_MAC): str,
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
})


class CrowConfigFlowHandler(ConfigFlow, domain=DOMAIN):

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                # info = await validate_input(self.hass, user_input)

                return self.async_create_entry(title=user_input[CONF_PANEL_MAC], data=user_input)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
