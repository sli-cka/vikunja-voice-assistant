"""Config flow for Vikunja Todo AI integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, CONF_OPENAI_API_KEY, CONF_OPENAI_MODEL, DEFAULT_MODEL, MODEL_OPTIONS
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vikunja Todo AI."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Format the URL by appending /api/v1 if it's not already there
            base_url = user_input[CONF_URL].rstrip('/')
            if not base_url.endswith('/api/v1'):
                api_url = f"{base_url}/api/v1"
            else:
                api_url = base_url
                
            # Validate the inputs
            vikunja_api = VikunjaAPI(
                api_url,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD]
            )
            
            # Test the connection
            success = await self.hass.async_add_executor_job(vikunja_api.authenticate)
            
            if success:
                # Save the formatted URL
                user_input[CONF_URL] = api_url
                
                # Avoid duplicate entries
                await self.async_set_unique_id(f"vikunja_{user_input[CONF_USERNAME]}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"Vikunja ({user_input[CONF_USERNAME]})",
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_OPENAI_API_KEY): str,
                    vol.Required(CONF_OPENAI_MODEL, default=DEFAULT_MODEL): vol.In(MODEL_OPTIONS),
                }
            ),
            errors=errors,
        )