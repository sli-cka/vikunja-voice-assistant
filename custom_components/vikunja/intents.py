"""Intent handlers for the Vikunja integration."""
from __future__ import annotations

import logging
from homeassistant.helpers import intent

from .task_handler import process_task
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VikunjaAddTaskIntentHandler(intent.IntentHandler):
    intent_type = "VikunjaAddTask"

    def __init__(self, hass, user_cache_provider):
        """user_cache_provider: callable returning list of user dicts."""
        self.hass = hass
        self._user_cache_provider = user_cache_provider

    async def async_handle(self, call: intent.Intent):  # type: ignore[override]
        slots = call.slots
        task_description = slots.get("task_description", {}).get("value", "")
        response = intent.IntentResponse(language=call.language)
        if not task_description.strip():
            response.async_set_speech("I couldn't understand what task you wanted to add. Please try again.")
            return response
        success, message, _title = await process_task(self.hass, task_description, self._user_cache_provider())
        response.async_set_speech(message)
        return response


def register_intents(hass, user_cache_provider) -> None:
    """Register all intents for the integration."""
    try:
        intent.async_register(hass, VikunjaAddTaskIntentHandler(hass, user_cache_provider))
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Failed to register intents for %s: %s", DOMAIN, err)
