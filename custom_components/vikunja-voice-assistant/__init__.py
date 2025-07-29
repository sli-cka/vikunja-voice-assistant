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
    CONF_VIKUNJA_URL,
    CONF_DUE_DATE,
    CONF_VOICE_CORRECTION, 
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
        CONF_DUE_DATE: entry.data[CONF_DUE_DATE],
        CONF_VOICE_CORRECTION: entry.data[CONF_VOICE_CORRECTION]
    }
    
    # Copy custom sentences
    await hass.async_add_executor_job(copy_custom_sentences, hass)
    
    # Create the task handling function that both conversation and voice can use
    async def handle_vikunja_task(task_description: str):
        """
        Handle creating a Vikunja task from a description.
        Returns: tuple (success: bool, message: str, task_title: str)
        """
        domain_config = hass.data.get(DOMAIN, {})
        vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
        vikunja_api_token = domain_config.get(CONF_VIKUNJA_API_TOKEN)
        openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
        openai_model = domain_config.get(CONF_OPENAI_MODEL)
        default_due_date = domain_config.get(CONF_DUE_DATE, "none")
        voice_correction = domain_config.get(CONF_VOICE_CORRECTION, True)
        
        if not all([vikunja_url, vikunja_api_token, openai_api_key]):
            _LOGGER.error("Missing configuration for Vikunja voice assistant")
            return False, "Configuration error. Please check your Vikunja and OpenAI settings.", ""
            
        vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_token)
        
        # Get all projects from Vikunja
        projects = await hass.async_add_executor_job(vikunja_api.get_projects)
        
        # Get all labels from Vikunja
        labels = await hass.async_add_executor_job(vikunja_api.get_labels)
        
        
            # Process with OpenAI
        openai_response = await process_with_openai(
            task_description, 
            projects, 
            labels,
            openai_api_key, 
            openai_model, 
            default_due_date,
            voice_correction
        )
        
        if not openai_response:
            _LOGGER.error("Failed to process with OpenAI")
            return False, "Sorry, I couldn't process your task due to a connection error. Please try again later.", ""
        
        # Log the response for debugging
        _LOGGER.debug("OpenAI response: %s", openai_response)
        
        try:
            # Parse the response
            response_data = json.loads(openai_response)
            task_data = response_data.get("task_data", {})
            labels_to_create = response_data.get("labels_to_create", [])
            
            # Validate required fields
            if not task_data.get("title"):
                _LOGGER.error("Missing required 'title' field in task data")
                return False, "Sorry, I couldn't understand what task you wanted to create. Please try again.", ""
            
            # Create any new labels that are needed
            created_label_ids = []
            if labels_to_create:
                for label_name in labels_to_create:
                    # Check if label already exists (case-insensitive)
                    existing_label = None
                    for label in labels:
                        if label.get("title", "").lower() == label_name.lower():
                            existing_label = label
                            break
                    
                    if existing_label:
                        created_label_ids.append(existing_label["id"])
                        _LOGGER.info(f"Using existing label: {label_name} (ID: {existing_label['id']})")
                    else:
                        # Create new label
                        new_label = await hass.async_add_executor_job(
                            lambda name=label_name: vikunja_api.create_label({"title": name})
                        )
                        if new_label:
                            created_label_ids.append(new_label["id"])
                            _LOGGER.info(f"Created new label: {label_name} (ID: {new_label['id']})")
                        else:
                            _LOGGER.warning(f"Failed to create label: {label_name}")
            
            # Add created label IDs to existing label_ids
            existing_label_ids = task_data.get("label_ids", [])
            all_label_ids = existing_label_ids + created_label_ids
            
            if all_label_ids:
                task_data["label_ids"] = all_label_ids
            
            # Remove labels_to_create from task_data as it's not needed for Vikunja API
            task_data.pop("labels_to_create", None)
            
            # Send request to Vikunja
            result = await hass.async_add_executor_job(
                lambda: vikunja_api.add_task(task_data)
            )
            
            if result:
                task_title = task_data.get("title")
                labels_msg = ""
                if all_label_ids:
                    labels_msg = f" with {len(all_label_ids)} label(s)"
                _LOGGER.info("Successfully created task: %s%s", task_title, labels_msg)
                return True, f"Successfully added task: {task_title}{labels_msg}", task_title
            else:
                _LOGGER.error("Failed to create task in Vikunja")
                return False, "Sorry, I couldn't add the task to Vikunja. Please check your Vikunja connection.", ""
                
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to parse OpenAI response as JSON: %s", err)
            return False, "Sorry, there was an error processing your task. Please try again.", ""
        except Exception as err:
            _LOGGER.error("Unexpected error creating task: %s", err)
            return False, "Sorry, an unexpected error occurred. Please try again.", ""

    # Create a proper intent handler class
    class VikunjaAddTaskIntentHandler(intent.IntentHandler):
        """Handle VikunjaAddTask intents."""
        
        def __init__(self):
            self.intent_type = "VikunjaAddTask"  # Explicitly set intent_type
        
        async def async_handle(self, call: intent.Intent):
            """Handle the intent."""
            slots = call.slots
            task_description = slots.get("task_description", {}).get("value", "")
            
            response = intent.IntentResponse(language=call.language)
            
            if not task_description.strip():
                response.async_set_speech("I couldn't understand what task you wanted to add. Please try again.")
                return response
            
            # Process the task and get the result
            success, message, task_title = await handle_vikunja_task(task_description)
            
            if success:
                response.async_set_speech(message)
            else:
                response.async_set_speech(message)
                
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