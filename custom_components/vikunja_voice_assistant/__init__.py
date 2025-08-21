import logging
import os
import json
import asyncio
from homeassistant.helpers import intent
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_VIKUNJA_API_TOKEN,
    CONF_OPENAI_API_KEY,
    CONF_VIKUNJA_URL,
    CONF_DUE_DATE,
    CONF_VOICE_CORRECTION, 
    CONF_AUTO_VOICE_LABEL,
)
from .vikunja_api import VikunjaAPI
from .openai_api import OpenAIAPI
from .services import setup_services

_LOGGER = logging.getLogger(__name__)

def copy_custom_sentences(hass: HomeAssistant) -> None:
    """Copy bundled custom sentences into Home Assistant's expected directory.

    Only copies when source exists and when the target file is missing or older.
    """
    source_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "custom_sentences")
    if not os.path.exists(source_dir):
        return
    target_root = os.path.join(hass.config.config_dir, "custom_sentences")
    os.makedirs(target_root, exist_ok=True)
    for lang in os.listdir(source_dir):
        src_lang = os.path.join(source_dir, lang)
        if not os.path.isdir(src_lang):
            continue
        dst_lang = os.path.join(target_root, lang)
        os.makedirs(dst_lang, exist_ok=True)
        for fname in os.listdir(src_lang):
            if not fname.endswith(".yaml"):
                continue
            src_file = os.path.join(src_lang, fname)
            dst_file = os.path.join(dst_lang, fname)
            if not os.path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                with open(src_file, "r", encoding="utf-8") as src, open(dst_file, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

async def async_setup(hass: HomeAssistant, config):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data[DOMAIN] = {
        CONF_VIKUNJA_URL: entry.data[CONF_VIKUNJA_URL],
        CONF_VIKUNJA_API_TOKEN: entry.data[CONF_VIKUNJA_API_TOKEN],
        CONF_OPENAI_API_KEY: entry.data[CONF_OPENAI_API_KEY],
        CONF_DUE_DATE: entry.data[CONF_DUE_DATE],
        CONF_VOICE_CORRECTION: entry.data[CONF_VOICE_CORRECTION],
        CONF_AUTO_VOICE_LABEL: entry.data.get(CONF_AUTO_VOICE_LABEL, True)
    }

    async def handle_vikunja_task(task_description: str):
        """Returns (success, user_message, created_task_title)"""
        domain_config = hass.data.get(DOMAIN, {})
        vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
        vikunja_api_token = domain_config.get(CONF_VIKUNJA_API_TOKEN)
        openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
        default_due_date = domain_config.get(CONF_DUE_DATE, "none")
        voice_correction = domain_config.get(CONF_VOICE_CORRECTION, True)
        auto_voice_label = domain_config.get(CONF_AUTO_VOICE_LABEL, True)
        
        if not all([vikunja_url, vikunja_api_token, openai_api_key]):
            _LOGGER.error("Missing configuration for Vikunja voice assistant")
            return False, "Configuration error. Please check your Vikunja and OpenAI settings.", ""
            
        vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_token)
        projects, labels = await asyncio.gather(
            hass.async_add_executor_job(vikunja_api.get_projects),
            hass.async_add_executor_job(vikunja_api.get_labels),
        )

        voice_label_id = None
        if auto_voice_label:
            try:
                for lbl in labels or []:
                    if isinstance(lbl, dict) and lbl.get("title", "").lower() == "voice":
                        voice_label_id = lbl.get("id")
                        break
                if voice_label_id is None:
                    voice_label = await hass.async_add_executor_job(
                        vikunja_api.create_label, "voice"
                    )
                    if voice_label:
                        voice_label_id = voice_label.get("id")
            except Exception as label_err:
                _LOGGER.error("Could not ensure 'voice' label exists: %s", label_err)
        openai_client = OpenAIAPI(openai_api_key)
        openai_response = await hass.async_add_executor_job(
            lambda: openai_client.create_task_from_description(
                task_description,
                projects,
                labels,
                default_due_date,
                voice_correction,
            )
        )
        if not openai_response:
            _LOGGER.error("Failed to process task with OpenAI")
            return False, "Sorry, I couldn't process your task due to a connection error. Please try again later.", ""
        try:
            # openai_response is already a dict
            response_data = openai_response if isinstance(openai_response, dict) else json.loads(openai_response)
            task_data = response_data.get("task_data", {})
            if not task_data.get("title"):
                _LOGGER.error("Missing required 'title' field in task data")
                return False, "Sorry, I couldn't understand what task you wanted to create. Please try again.", ""
            # Extract labels, create task, then attach labels
            extracted_label_ids = []
            if isinstance(task_data, dict) and task_data.get("label_ids"):
                existing_label_ids = {l.get("id") for l in (labels or []) if isinstance(l, dict)}
                for lid in task_data.get("label_ids", []):
                    if lid in existing_label_ids:
                        extracted_label_ids.append(lid)
                task_data.pop("label_ids", None)
            result = await hass.async_add_executor_job(lambda: vikunja_api.add_task(task_data))
            if result:
                try:
                    task_id = result.get("id") if isinstance(result, dict) else None
                    if task_id:
                        label_ids_to_attach = list(dict.fromkeys(extracted_label_ids))  # preserve order
                        if auto_voice_label and voice_label_id:
                            if voice_label_id not in label_ids_to_attach:
                                label_ids_to_attach.append(voice_label_id)
                        for lid in label_ids_to_attach:
                            attach_success = await hass.async_add_executor_job(
                                vikunja_api.add_label_to_task, task_id, lid
                            )
                            if not attach_success:
                                _LOGGER.error("Failed to attach label %s to task %s", lid, task_id)
                except Exception as attach_err:  # noqa: BLE001
                    _LOGGER.error("Error attaching labels to task: %s", attach_err)

            if result:
                task_title = task_data.get("title")
                _LOGGER.info("Created Vikunja task '%s'", task_title)
                return True, f"Successfully added task: {task_title}", task_title
            else:
                _LOGGER.error("Failed to create task in Vikunja")
                return False, "Sorry, I couldn't add the task to Vikunja. Please check your Vikunja connection.", ""
        except json.JSONDecodeError as err:  # noqa: BLE001
            _LOGGER.error("Failed to parse OpenAI response as JSON: %s", err)
            return False, "Sorry, there was an error processing your task. Please try again.", ""
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unexpected error creating task: %s", err)
            return False, "Sorry, an unexpected error occurred. Please try again.", ""

    class VikunjaAddTaskIntentHandler(intent.IntentHandler):
        def __init__(self):
            self.intent_type = "VikunjaAddTask"
        
        async def async_handle(self, call: intent.Intent):
            """Handle the intent invocation from conversation agent."""
            slots = call.slots
            task_description = slots.get("task_description", {}).get("value", "")
            
            response = intent.IntentResponse(language=call.language)
            
            if not task_description.strip():
                response.async_set_speech("I couldn't understand what task you wanted to add. Please try again.")
                return response
            success, message, task_title = await handle_vikunja_task(task_description)
            
            if success:
                response.async_set_speech(message)
            else:
                response.async_set_speech(message)
                
            return response   

    intent.async_register(hass, VikunjaAddTaskIntentHandler())
    setup_services(hass)
    await hass.services.async_call("conversation", "reload", {})
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry (placeholder for future cleanup)."""
    return True