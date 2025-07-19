import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN, 
    CONF_OPENAI_API_KEY, 
    CONF_OPENAI_MODEL, 
    DEFAULT_MODEL, 
    MODEL_OPTIONS,
    CONF_VIKUNJA_URL,
    CONF_VIKUNJA_API_TOKEN,
    CONF_DUE_DATE,  
    DUE_DATE_OPTIONS,
    CONF_VOICE_CORRECTION, 
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
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1
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

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VIKUNJA_URL): str,
                    vol.Required(CONF_VIKUNJA_API_TOKEN): str,
                    vol.Required(CONF_OPENAI_API_KEY): str,
                    vol.Required(CONF_OPENAI_MODEL, default=DEFAULT_MODEL): vol.In(MODEL_OPTIONS),
                    vol.Required(CONF_VOICE_CORRECTION, default=True): cv.boolean,
                    vol.Required(CONF_DUE_DATE, default="tomorrow"): vol.In(DUE_DATE_OPTIONS),
                }
            ),
            errors=errors,
        )