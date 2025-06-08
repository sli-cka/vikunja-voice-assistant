"""Services for Vikunja voice assistant integration."""
import logging
import json
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_URL, CONF_API_TOKEN

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
    vikunja_url = domain_config.get(CONF_URL)
    api_token = domain_config.get(CONF_API_TOKEN)
    
    if not all([vikunja_url, api_token]):
        _LOGGER.error("Missing configuration for Vikunja voice assistant")
        return
        
    vikunja_api = VikunjaAPI(vikunja_url, api_token)
    
    async def create_task(call: ServiceCall):
        """Create a task in Vikunja."""
        task_data = call.data.copy()
        
        await hass.async_add_executor_job(
            lambda: vikunja_api.add_task(task_data)
        )
    
    # Register services
    hass.services.async_register(
        DOMAIN, "create_task", create_task, schema=CREATE_TASK_SCHEMA
    )