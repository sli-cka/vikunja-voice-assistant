"""Initialize the Vikunja voice assistant integration."""
import logging
import os
import json
from homeassistant.helpers import intent
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_VIKUNJA_API_TOKEN,
    CONF_OPENAI_API_KEY,
    CONF_OPENAI_MODEL,
    CONF_VIKUNJA_URL
)
from .vikunja_api import VikunjaAPI
from .process_with_openai import process_with_openai
from .services import setup_services

_LOGGER = logging.getLogger(__name__)

# Copy custom sentences to the correct location
def copy_custom_sentences(hass: HomeAssistant):
    component_path = os.path.dirname(os.path.realpath(__file__))
    source_sentences_dir = os.path.join(component_path, "custom_sentences")
    
    if not os.path.exists(source_sentences_dir):
        _LOGGER.debug("No custom sentences directory found")
        return
        
    target_dir = os.path.join(hass.config.config_dir, "custom_sentences")
    
    # Create target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    # Copy language directories
    for lang_dir in os.listdir(source_sentences_dir):
        source_lang_dir = os.path.join(source_sentences_dir, lang_dir)
        if os.path.isdir(source_lang_dir):
            target_lang_dir = os.path.join(target_dir, lang_dir)
            if not os.path.exists(target_lang_dir):
                os.makedirs(target_lang_dir, exist_ok=True)
            
            # Copy YAML files
            for yaml_file in os.listdir(source_lang_dir):
                if yaml_file.endswith('.yaml'):
                    source_file = os.path.join(source_lang_dir, yaml_file)
                    target_file = os.path.join(target_lang_dir, yaml_file)
                    
                    # Only copy if target doesn't exist or is older
                    if not os.path.exists(target_file) or os.path.getmtime(source_file) > os.path.getmtime(target_file):
                        with open(source_file, 'r') as src, open(target_file, 'w') as dst:
                            dst.write(src.read())
                        _LOGGER.debug(f"Copied custom sentences: {yaml_file}")

async def async_setup(hass: HomeAssistant, config):
    """Set up the Vikunja voice assistant component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Vikunja voice assistant from a config entry."""
    # Store config data in hass.data
    hass.data[DOMAIN] = {
        CONF_VIKUNJA_URL: entry.data[CONF_VIKUNJA_URL],
        CONF_VIKUNJA_API_TOKEN: entry.data[CONF_VIKUNJA_API_TOKEN],
        CONF_OPENAI_API_KEY: entry.data[CONF_OPENAI_API_KEY],
        CONF_OPENAI_MODEL: entry.data[CONF_OPENAI_MODEL],
    }
    
    # Copy custom sentences
    await hass.async_add_executor_job(copy_custom_sentences, hass)
    
    # Create the task handling function that both conversation and voice can use
    async def handle_vikunja_task(task_description: str):
        """Process a task request from any input source."""
        domain_config = hass.data.get(DOMAIN, {})
        vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
        vikunja_api_token = domain_config.get(CONF_VIKUNJA_API_TOKEN)
        openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
        openai_model = domain_config.get(CONF_OPENAI_MODEL)
        
        if not all([vikunja_url, vikunja_api_token, openai_api_key]):
            _LOGGER.error("Missing configuration for Vikunja voice assistant")
            return
            
        vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_token)
        
        # Get all projects from Vikunja
        projects = await hass.async_add_executor_job(vikunja_api.get_projects)
        
        # Process with OpenAI
        openai_response = await process_with_openai(task_description, projects, openai_api_key, openai_model)
        
        if not openai_response:
            _LOGGER.error("Failed to process with OpenAI")
            return
            
        # Send request to Vikunja
        await hass.async_add_executor_job(
            lambda: vikunja_api.add_task(json.loads(openai_response))
        )

    # Create a proper intent handler class
    class VikunjaAddTaskIntentHandler(intent.IntentHandler):
        """Handle VikunjaAddTask intents."""
        
        def __init__(self):
            self.intent_type = "VikunjaAddTask"  # Explicitly set intent_type
        
        async def async_handle(self, call: intent.Intent):
            """Handle the intent."""
            slots = call.slots
            task_description = slots.get("task_description", {}).get("value", "")
            
            # Process the task
            await handle_vikunja_task(task_description)
            
            response = intent.IntentResponse(language=call.language)
            response.async_set_speech(f"Adding task: {task_description}")
            return response   
    
    # Register the intent handler
    intent.async_register(hass, VikunjaAddTaskIntentHandler())
    
    # Set up services
    setup_services(hass)
    
    # Reload conversation agent to pick up the new sentences
    await hass.services.async_call("conversation", "reload", {})
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Nothing to unload
    return True