import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN, 
    CONF_OPENAI_API_KEY, 
    CONF_VIKUNJA_URL,
    CONF_VIKUNJA_API_TOKEN,
    CONF_DUE_DATE,  
    DUE_DATE_OPTIONS,
    CONF_VOICE_CORRECTION, 
    CONF_AUTO_VOICE_LABEL,
)
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _test_openai_connection(self, api_key: str) -> bool:
        """Test OpenAI API connection."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Simple test payload to validate API key
        payload = {
            "model": "gpt-5-nano",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1,
            "reasoning_effort": "minimal"
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    # Accept both 200 (success) and 400 (bad request but valid auth)
                    # 401 would indicate invalid API key
                    return response.status != 401
        except Exception as err:
            _LOGGER.error("Failed to test OpenAI connection: %s", err)
            return False

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        # Default values to show in the form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_VIKUNJA_URL, default=""): str,
                vol.Required(CONF_VIKUNJA_API_TOKEN, default=""): str,
                vol.Required(CONF_OPENAI_API_KEY, default=""): str,
                vol.Required(CONF_VOICE_CORRECTION, default=True): cv.boolean,
                vol.Required(CONF_AUTO_VOICE_LABEL, default=True): cv.boolean,
                vol.Required(CONF_DUE_DATE, default="tomorrow"): vol.In(DUE_DATE_OPTIONS),
            }
        )

        if user_input is not None:
            # Strip spaces from API keys and tokens
            user_input[CONF_VIKUNJA_API_TOKEN] = user_input[CONF_VIKUNJA_API_TOKEN].strip()
            user_input[CONF_OPENAI_API_KEY] = user_input[CONF_OPENAI_API_KEY].strip()
            
            base_url = user_input[CONF_VIKUNJA_URL].rstrip('/')
            if not base_url.endswith('/api/v1'):
                api_url = f"{base_url}/api/v1"
            else:
                api_url = base_url
                
            vikunja_api = VikunjaAPI(
                api_url,
                user_input[CONF_VIKUNJA_API_TOKEN]
            )
            
            # Test the Vikunja connection
            vikunja_success = await self.hass.async_add_executor_job(vikunja_api.test_connection)
            
            if not vikunja_success:
                errors["base"] = "cannot_connect"
            else:
                # Test OpenAI connection
                openai_success = await self._test_openai_connection(user_input[CONF_OPENAI_API_KEY])
                
                if not openai_success:
                    errors[CONF_OPENAI_API_KEY] = "invalid_openai_key"
                else:
                    # Save the formatted URL
                    user_input[CONF_VIKUNJA_URL] = api_url
                    
                    # Avoid duplicate entries
                    await self.async_set_unique_id(f"vikunja_{api_url}")
                    self._abort_if_unique_id_configured()
                    
                    return self.async_create_entry(
                        title=f"Vikunja ({api_url})",
                        data=user_input
                    )
            
            # If there are errors, update the schema with the user's input as defaults
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_VIKUNJA_URL, default=user_input.get(CONF_VIKUNJA_URL, "")): str,
                    vol.Required(CONF_VIKUNJA_API_TOKEN, default=user_input.get(CONF_VIKUNJA_API_TOKEN, "")): str,
                    vol.Required(CONF_OPENAI_API_KEY, default=user_input.get(CONF_OPENAI_API_KEY, "")): str,
                    vol.Required(CONF_VOICE_CORRECTION, default=user_input.get(CONF_VOICE_CORRECTION, True)): cv.boolean,
                    vol.Required(CONF_AUTO_VOICE_LABEL, default=user_input.get(CONF_AUTO_VOICE_LABEL, True)): cv.boolean,
                    vol.Required(CONF_DUE_DATE, default=user_input.get(CONF_DUE_DATE, "tomorrow")): vol.In(DUE_DATE_OPTIONS),
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )