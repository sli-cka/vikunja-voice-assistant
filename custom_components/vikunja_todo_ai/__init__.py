"""The Vikunja Todo AI integration."""
import logging
import voluptuous as vol
from .services import setup_services
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    CONF_URL, 
    CONF_USERNAME, 
    CONF_PASSWORD,
)
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_OPENAI_CONVERSATION

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_URL): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_OPENAI_CONVERSATION): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Vikunja Todo AI component from yaml configuration."""
    hass.data[DOMAIN] = {}
    
    if DOMAIN in config:
        # Store yaml configuration to be accessible by other components
        hass.data[DOMAIN].update({
            CONF_URL: config[DOMAIN][CONF_URL],
            CONF_USERNAME: config[DOMAIN][CONF_USERNAME],
            CONF_PASSWORD: config[DOMAIN][CONF_PASSWORD],
            CONF_OPENAI_CONVERSATION: config[DOMAIN][CONF_OPENAI_CONVERSATION],
        })
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Vikunja Todo AI from a config entry."""
    setup_services(hass)
    # Store config entry data
    hass.data.setdefault(DOMAIN, {}).update({
        CONF_URL: entry.data[CONF_URL],
        CONF_USERNAME: entry.data[CONF_USERNAME],
        CONF_PASSWORD: entry.data[CONF_PASSWORD],
        CONF_OPENAI_CONVERSATION: entry.data[CONF_OPENAI_CONVERSATION],
    })
    
    # Register services
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "automation")
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(entry, "automation")
    return True