"""Config flow for Vikunja Todo AI integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_OPENAI_CONVERSATION
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

class VikunjaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vikunja Todo AI."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the inputs
            vikunja_api = VikunjaAPI(
                user_input[CONF_URL],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD]
            )
            
            # Test the connection
            success = await self.hass.async_add_executor_job(vikunja_api.authenticate)
            
            if success:
                return self.async_create_entry(
                    title="Vikunja Todo AI",
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_OPENAI_CONVERSATION): str,
                }
            ),
            errors=errors,
        )
