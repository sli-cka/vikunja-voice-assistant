"""Service registrations for Vikunja Voice Assistant."""

import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.config_entries import ConfigEntryState
from .const import DOMAIN, CONF_VIKUNJA_URL, CONF_VIKUNJA_API_KEY
from .api.vikunja_api import VikunjaAPI, VikunjaAuthenticationError

_LOGGER = logging.getLogger(__name__)

CREATE_TASK_SCHEMA = vol.Schema(
    {
        vol.Required("title"): cv.string,
        vol.Optional("description"): cv.string,
        vol.Optional("project_id"): cv.positive_int,
        vol.Optional("due_date"): cv.string,
    }
)


def setup_services(hass: HomeAssistant):
    """Register the create_task service."""
    domain_config = hass.data.get(DOMAIN, {})
    vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
    vikunja_api_key = domain_config.get(CONF_VIKUNJA_API_KEY)

    if not all([vikunja_url, vikunja_api_key]):
        _LOGGER.error("Missing configuration for Vikunja voice assistant")
        return

    vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_key)

    async def create_task(call: ServiceCall):
        """Create a task in Vikunja."""
        task_data = call.data.copy()

        try:
            result = await hass.async_add_executor_job(
                lambda: vikunja_api.add_task(task_data)
            )

            if result:
                _LOGGER.info(
                    "Successfully created task via service: %s",
                    task_data.get("title", "Unknown"),
                )
            else:
                _LOGGER.error(
                    "Failed to create task via service: %s",
                    task_data.get("title", "Unknown"),
                )
                raise Exception("Failed to create task in Vikunja")
        except VikunjaAuthenticationError:
            _LOGGER.error("Authentication failed - triggering reauth flow")
            # Find the config entry and trigger reauth
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.state == ConfigEntryState.LOADED:
                    entry.async_start_reauth(hass)
                    break
            raise Exception("Vikunja authentication failed. Please reauthenticate.") from None

    hass.services.async_register(
        DOMAIN, "create_task", create_task, schema=CREATE_TASK_SCHEMA
    )
