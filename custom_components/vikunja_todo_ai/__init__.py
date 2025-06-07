"""The Vikunja Todo AI integration."""
import logging
import voluptuous as vol
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
    """Set up the Vikunja Todo AI component."""
    hass.data[DOMAIN] = {}
    
    if DOMAIN not in config:
        return True
        
    hass.data[DOMAIN] = {
        CONF_URL: config[DOMAIN][CONF_URL],
        CONF_USERNAME: config[DOMAIN][CONF_USERNAME],
        CONF_PASSWORD: config[DOMAIN][CONF_PASSWORD],
        CONF_OPENAI_CONVERSATION: config[DOMAIN][CONF_OPENAI_CONVERSATION],
    }
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Vikunja Todo AI from a config entry."""
    # Load automations
    hass.helpers.discovery.load_platform("automation", DOMAIN, {}, entry)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    return True
