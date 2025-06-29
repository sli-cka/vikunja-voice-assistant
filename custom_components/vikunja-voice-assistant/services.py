"""Services for Vikunja voice assistant integration."""
import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from .const import (
    DOMAIN,
    CONF_VIKUNJA_URL,  # Add these two constants
    CONF_VIKUNJA_API_TOKEN
)

from .const import DOMAIN
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

CREATE_TASK_SCHEMA = vol.Schema({
    vol.Required("title"): cv.string,
    vol.Optional("description"): cv.string,
    vol.Optional("project_id"): cv.positive_int,
    vol.Optional("due_date"): cv.string,
})

def setup_services(hass: HomeAssistant):
    """Set up services for Vikunja integration."""
    domain_config = hass.data.get(DOMAIN, {})
    vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
    vikunja_api_token = domain_config.get(CONF_VIKUNJA_API_TOKEN)
    
    if not all([vikunja_url, vikunja_api_token]):
        _LOGGER.error("Missing configuration for Vikunja voice assistant")
        return
        
    vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_token)
    
    async def create_task(call: ServiceCall):
        """Create a task in Vikunja."""
        task_data = call.data.copy()
        
        result = await hass.async_add_executor_job(
            lambda: vikunja_api.add_task(task_data)
        )
        
        if result:
            _LOGGER.info("Successfully created task via service: %s", task_data.get("title", "Unknown"))
        else:
            _LOGGER.error("Failed to create task via service: %s", task_data.get("title", "Unknown"))
            raise Exception("Failed to create task in Vikunja")
    
    # Register services
    hass.services.async_register(
        DOMAIN, "create_task", create_task, schema=CREATE_TASK_SCHEMA
    )