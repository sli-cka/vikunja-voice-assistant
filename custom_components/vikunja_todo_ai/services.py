"""Services for Vikunja Todo AI integration."""
import logging
import json
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD

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
    username = domain_config.get(CONF_USERNAME)
    password = domain_config.get(CONF_PASSWORD)
    
    if not all([vikunja_url, username, password]):
        _LOGGER.error("Missing configuration for Vikunja Todo AI")
        return
        
    vikunja_api = VikunjaAPI(vikunja_url, username, password)
    
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