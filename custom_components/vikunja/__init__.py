import logging
import os
import json
import asyncio
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import intent
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    CONF_VIKUNJA_API_KEY,
    CONF_OPENAI_API_KEY,
    CONF_VIKUNJA_URL,
    CONF_DUE_DATE,
    CONF_VOICE_CORRECTION, 
    CONF_AUTO_VOICE_LABEL,
    CONF_ENABLE_USER_ASSIGN,
    USER_CACHE_FILENAME,
    USER_CACHE_REFRESH_HOURS,
)
from .vikunja_api import VikunjaAPI
from .openai_api import OpenAIAPI
from .services import setup_services

_LOGGER = logging.getLogger(__name__)

# Integration uses config entries only, but hassfest expects a CONFIG_SCHEMA when async_setup exists
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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
        CONF_VIKUNJA_API_KEY: entry.data[CONF_VIKUNJA_API_KEY],
        CONF_OPENAI_API_KEY: entry.data[CONF_OPENAI_API_KEY],
        CONF_DUE_DATE: entry.data[CONF_DUE_DATE],
        CONF_VOICE_CORRECTION: entry.data[CONF_VOICE_CORRECTION],
        CONF_AUTO_VOICE_LABEL: entry.data.get(CONF_AUTO_VOICE_LABEL, True),
        CONF_ENABLE_USER_ASSIGN: entry.data.get(CONF_ENABLE_USER_ASSIGN, False),
    }

    # --- User cache helpers ---
    cache_path = os.path.join(hass.config.config_dir, USER_CACHE_FILENAME)
    user_cache = {"users": [], "last_refresh": None}

    def _load_user_cache():
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and isinstance(data.get("users"), list):
                        return data
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Failed loading user cache: %s", err)
        return {"users": [], "last_refresh": None}

    def _save_user_cache(data):
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed saving user cache: %s", err)

    async def _refresh_user_cache(force: bool = False):
        """Refresh all users by searching A-Z if enabled."""
        if not hass.data[DOMAIN].get(CONF_ENABLE_USER_ASSIGN):
            return
        nonlocal user_cache
        if not force and user_cache.get("last_refresh"):
            # Check age
            try:
                from datetime import datetime, timezone
                last = datetime.fromisoformat(user_cache["last_refresh"].replace("Z", "+00:00"))
                age_hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
                if age_hours < USER_CACHE_REFRESH_HOURS:
                    return
            except Exception:  # noqa: BLE001
                pass
        domain_config = hass.data.get(DOMAIN, {})
        vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
        vikunja_api_key = domain_config.get(CONF_VIKUNJA_API_KEY)
        if not (vikunja_url and vikunja_api_key):
            return
        api = VikunjaAPI(vikunja_url, vikunja_api_key)
        # Only search vowels (including 'y') for efficiency; most names contain at least one
        letters = ['a', 'e', 'i', 'o', 'u', 'y']
        all_users = {}
        for letter in letters:
            try:
                users = await hass.async_add_executor_job(api.search_users, letter)
                for u in users:
                    if isinstance(u, dict) and u.get("id") is not None:
                        key = str(u.get("id"))
                        if key not in all_users:
                            all_users[key] = {
                                "id": u.get("id"),
                                "name": u.get("name"),
                                "username": u.get("username"),
                            }
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("User search failed for '%s': %s", letter, err)
        from datetime import datetime, timezone
        user_cache = {
            "users": list(all_users.values()),
            "last_refresh": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        await hass.async_add_executor_job(_save_user_cache, user_cache)
        _LOGGER.info("Vikunja user cache refreshed: %s users", len(user_cache["users"]))

    # Load cache at startup if feature enabled
    if hass.data[DOMAIN].get(CONF_ENABLE_USER_ASSIGN):
        user_cache = await hass.async_add_executor_job(_load_user_cache)
        # Schedule periodic refresh
        try:
            from datetime import timedelta
            from homeassistant.helpers.event import async_track_time_interval
            async def _scheduled_refresh(now):  # noqa: D401
                await _refresh_user_cache()
            async_track_time_interval(hass, _scheduled_refresh, timedelta(hours=USER_CACHE_REFRESH_HOURS))
            # Kick initial refresh if no users
            if not user_cache.get("users"):
                hass.async_create_task(_refresh_user_cache(force=True))
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to schedule user cache refresh: %s", err)

    async def handle_vikunja_task(task_description: str):
        """Returns (success, user_message, created_task_title)"""
        domain_config = hass.data.get(DOMAIN, {})
        vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
        vikunja_api_key = domain_config.get(CONF_VIKUNJA_API_KEY)
        openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
        default_due_date = domain_config.get(CONF_DUE_DATE, "none")
        voice_correction = domain_config.get(CONF_VOICE_CORRECTION, True)
        auto_voice_label = domain_config.get(CONF_AUTO_VOICE_LABEL, True)
        enable_user_assignment = domain_config.get(CONF_ENABLE_USER_ASSIGN, False)

        if not all([vikunja_url, vikunja_api_key, openai_api_key]):
            _LOGGER.error("Missing configuration for Vikunja voice assistant")
            return False, "Configuration error. Please check your Vikunja and OpenAI settings.", ""

        vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_key)
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
            except Exception as label_err:  # noqa: BLE001
                _LOGGER.error("Could not ensure 'voice' label exists: %s", label_err)

        openai_client = OpenAIAPI(openai_api_key)
        users_for_prompt = user_cache.get("users", []) if enable_user_assignment else []
        # Use keyword args for new params to avoid positional issues
        openai_response = await hass.async_add_executor_job(
            lambda: openai_client.create_task_from_description(
                task_description,
                projects,
                labels,
                default_due_date,
                voice_correction,
                users=users_for_prompt,
                enable_user_assignment=enable_user_assignment,
            )
        )
        if not openai_response:
            _LOGGER.error("Failed to process task with OpenAI")
            return False, "Sorry, I couldn't process your task due to a connection error. Please try again later.", ""
        try:
            response_data = openai_response if isinstance(openai_response, dict) else json.loads(openai_response)
            task_data = response_data.get("task_data", {})
            if not task_data.get("title"):
                _LOGGER.error("Missing required 'title' field in task data")
                return False, "Sorry, I couldn't understand what task you wanted to create. Please try again.", ""

            extracted_label_ids = []
            if isinstance(task_data, dict) and task_data.get("label_ids"):
                existing_label_ids = {l.get("id") for l in (labels or []) if isinstance(l, dict)}
                for lid in task_data.get("label_ids", []):
                    if lid in existing_label_ids:
                        extracted_label_ids.append(lid)
                task_data.pop("label_ids", None)

            assignee_username_or_name = task_data.pop("assignee", None)
            result = await hass.async_add_executor_job(lambda: vikunja_api.add_task(task_data))
            if result:
                try:
                    task_id = result.get("id") if isinstance(result, dict) else None
                    if task_id:
                        label_ids_to_attach = list(dict.fromkeys(extracted_label_ids))
                        if auto_voice_label and voice_label_id and voice_label_id not in label_ids_to_attach:
                            label_ids_to_attach.append(voice_label_id)
                        for lid in label_ids_to_attach:
                            attach_success = await hass.async_add_executor_job(
                                vikunja_api.add_label_to_task, task_id, lid
                            )
                            if not attach_success:
                                _LOGGER.error("Failed to attach label %s to task %s", lid, task_id)

                        if enable_user_assignment and assignee_username_or_name:
                            try:
                                lookup = assignee_username_or_name.strip().lower()
                                uid = None
                                for u in user_cache.get("users", []):
                                    uname = str(u.get("username", "")).lower()
                                    name = str(u.get("name", "")).lower()
                                    if lookup == uname or lookup == name:
                                        uid = u.get("id")
                                        break
                                if uid is not None:
                                    assign_ok = await hass.async_add_executor_job(
                                        vikunja_api.assign_user_to_task, task_id, uid
                                    )
                                    if not assign_ok:
                                        _LOGGER.error("Failed to assign user %s to task %s", lookup, task_id)
                                else:
                                    _LOGGER.warning("Assignee '%s' not found in cached users", assignee_username_or_name)
                            except Exception as assign_err:  # noqa: BLE001
                                _LOGGER.error("Error assigning user: %s", assign_err)
                except Exception as attach_err:  # noqa: BLE001
                    _LOGGER.error("Error attaching labels to task: %s", attach_err)

            if result:
                task_title = task_data.get("title")
                _LOGGER.info("Created Vikunja task '%s'", task_title)
                return True, f"Successfully added task: {task_title}", task_title
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
    # Manual refresh service (only if feature enabled)
    if hass.data[DOMAIN].get(CONF_ENABLE_USER_ASSIGN):
        async def _handle_refresh_users(call):  # noqa: D401
            await _refresh_user_cache(force=True)
        hass.services.async_register(DOMAIN, "refresh_user_cache", _handle_refresh_users)
    await hass.services.async_call("conversation", "reload", {})
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry (placeholder for future cleanup)."""
    return True