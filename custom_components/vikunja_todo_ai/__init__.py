"""The Vikunja Todo AI integration."""
import logging
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_URL
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_API_TOKEN, CONF_OPENAI_API_KEY, CONF_OPENAI_MODEL, DEFAULT_MODEL
from .services import setup_services

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Vikunja Todo AI component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    
    if DOMAIN in config:
        # Store yaml configuration to be accessible by other components
        hass.data[DOMAIN].update({
            CONF_URL: config[DOMAIN][CONF_URL],
            CONF_API_TOKEN: config[DOMAIN][CONF_API_TOKEN],
            CONF_OPENAI_API_KEY: config[DOMAIN][CONF_OPENAI_API_KEY],
            CONF_OPENAI_MODEL: config[DOMAIN].get(CONF_OPENAI_MODEL, DEFAULT_MODEL),
        })
        
        # Setup services for YAML config
        setup_services(hass)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vikunja Todo AI from a config entry."""
    # Store config entry data
    hass.data.setdefault(DOMAIN, {}).update({
        CONF_URL: entry.data[CONF_URL],
        CONF_API_TOKEN: entry.data[CONF_API_TOKEN],
        CONF_OPENAI_API_KEY: entry.data[CONF_OPENAI_API_KEY],
        CONF_OPENAI_MODEL: entry.data.get(CONF_OPENAI_MODEL, DEFAULT_MODEL),
    })
    
    # Setup services
    setup_services(hass)
    
    # Register automation platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "automation")
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "automation")
    return True