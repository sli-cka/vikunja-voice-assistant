import logging
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_VIKUNJA_URL
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_VIKUNJA_API_TOKEN, CONF_OPENAI_API_KEY, CONF_OPENAI_MODEL, DEFAULT_MODEL
from .services import setup_services
from .automation import setup_automation

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    
    if DOMAIN in config:
        # Store yaml configuration to be accessible by other components
        hass.data[DOMAIN].update({
            CONF_VIKUNJA_URL: config[DOMAIN].get(CONF_VIKUNJA_URL),
            CONF_VIKUNJA_API_TOKEN: config[DOMAIN].get(CONF_VIKUNJA_API_TOKEN),
            CONF_OPENAI_API_KEY: config[DOMAIN].get(CONF_OPENAI_API_KEY),
            CONF_OPENAI_MODEL: config[DOMAIN].get(CONF_OPENAI_MODEL, DEFAULT_MODEL),
        })
        
        # Setup services for YAML config
        setup_services(hass)
        
        # Setup automation directly
        await setup_automation(hass, config[DOMAIN])
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Store config entry data
    hass.data.setdefault(DOMAIN, {}).update({
        CONF_VIKUNJA_URL: entry.data.get(CONF_VIKUNJA_URL),
        CONF_VIKUNJA_API_TOKEN: entry.data.get(CONF_VIKUNJA_API_TOKEN),
        CONF_OPENAI_API_KEY: entry.data.get(CONF_OPENAI_API_KEY),
        CONF_OPENAI_MODEL: entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODEL),
    })
    
    # Setup services
    setup_services(hass)
    
    # Setup automation directly instead of using platforms
    await setup_automation(hass, dict(entry.data))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Since we're not using platforms, we just need to remove our event listener
    # This would be handled in the automation.py file
    return True