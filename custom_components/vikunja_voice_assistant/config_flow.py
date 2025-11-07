import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector  # added

from .const import (
    DOMAIN,
    CONF_OPENAI_API_KEY,
    CONF_VIKUNJA_URL,
    CONF_VIKUNJA_API_KEY,
    CONF_DUE_DATE,
    DUE_DATE_OPTIONS,
    CONF_VOICE_CORRECTION,
    CONF_AUTO_VOICE_LABEL,
    CONF_ENABLE_USER_ASSIGN,
    DUE_DATE_OPTION_LABELS,
    CONF_DETAILED_RESPONSE,
)
from .helpers.localization import get_language
from .api.vikunja_api import VikunjaAPI
from .user_cache import build_initial_user_cache_sync

_LOGGER = logging.getLogger(__name__)

DEFAULT_FORM_VALUES = {
    CONF_VIKUNJA_URL: "",
    CONF_VIKUNJA_API_KEY: "",
    CONF_OPENAI_API_KEY: "",
    CONF_VOICE_CORRECTION: True,
    CONF_AUTO_VOICE_LABEL: True,
    CONF_ENABLE_USER_ASSIGN: False,
    CONF_DUE_DATE: "tomorrow",
    CONF_DETAILED_RESPONSE: True,
}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for the Vikunja integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    _basic_input: dict | None = None

    async def _test_openai_connection(self, api_key: str) -> bool:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Simple test payload to validate API key
        payload = {
            "model": "gpt-5-nano",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 1,
            "reasoning_effort": "minimal",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    # Accept both 200 (success) and 400 (bad request but valid auth)
                    return response.status != 401
        except Exception as err:
            _LOGGER.error("Failed to test OpenAI connection: %s", err)
            return False

    def _build_due_date_selector(self) -> selector.SelectSelector:
        # Determine language for localized labels, fallback handled by lookup
        lang = get_language(self.hass)

        options = [
            selector.SelectOptionDict(
                value=value,
                label=(
                    DUE_DATE_OPTION_LABELS.get(value, {}).get(lang)
                    or DUE_DATE_OPTION_LABELS.get(value, {}).get("en", value)
                ),
            )
            for value in DUE_DATE_OPTIONS
        ]
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )

    # Build the data schema for the form
    def _build_data_schema(self, defaults: dict[str, Any] | None = None) -> vol.Schema:
        values: dict[str, Any] = {**DEFAULT_FORM_VALUES, **(defaults or {})}
        due_date_selector = self._build_due_date_selector()
        return vol.Schema(
            {
                vol.Required(CONF_VIKUNJA_URL, default=values[CONF_VIKUNJA_URL]): str,
                vol.Required(
                    CONF_VIKUNJA_API_KEY,
                    default=values[CONF_VIKUNJA_API_KEY],
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
                vol.Required(
                    CONF_OPENAI_API_KEY,
                    default=values[CONF_OPENAI_API_KEY],
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
                vol.Required(
                    CONF_VOICE_CORRECTION,
                    default=values[CONF_VOICE_CORRECTION],
                ): cv.boolean,
                vol.Required(
                    CONF_AUTO_VOICE_LABEL,
                    default=values[CONF_AUTO_VOICE_LABEL],
                ): cv.boolean,
                vol.Required(
                    CONF_ENABLE_USER_ASSIGN,
                    default=values[CONF_ENABLE_USER_ASSIGN],
                ): cv.boolean,
                vol.Required(
                    CONF_DUE_DATE,
                    default=values[CONF_DUE_DATE],
                ): due_date_selector,
                vol.Required(
                    CONF_DETAILED_RESPONSE,
                    default=values[CONF_DETAILED_RESPONSE],
                ): cv.boolean,
            }
        )

    # Process user input for both initial setup and reconfiguration
    async def _async_process_input(
        self,
        user_input: dict[str, Any],
        *,
        existing_entry: config_entries.ConfigEntry | None = None,
    ) -> tuple[FlowResult | None, dict[str, str], dict[str, Any]]:
        errors: dict[str, str] = {}
        sanitized: dict[str, Any] = dict(user_input)

        sanitized[CONF_VIKUNJA_URL] = sanitized[CONF_VIKUNJA_URL].strip()
        sanitized[CONF_VIKUNJA_API_KEY] = sanitized[CONF_VIKUNJA_API_KEY].strip()
        sanitized[CONF_OPENAI_API_KEY] = sanitized[CONF_OPENAI_API_KEY].strip()

        base_url = sanitized[CONF_VIKUNJA_URL].rstrip("/")
        api_url = base_url if base_url.endswith("/api/v1") else f"{base_url}/api/v1"

        vikunja_api = VikunjaAPI(api_url, sanitized[CONF_VIKUNJA_API_KEY])
        vikunja_success = await self.hass.async_add_executor_job(
            vikunja_api.test_connection
        )

        if not vikunja_success:
            errors["base"] = "cannot_connect"
        else:
            openai_success = await self._test_openai_connection(
                sanitized[CONF_OPENAI_API_KEY]
            )
            if not openai_success:
                errors[CONF_OPENAI_API_KEY] = "invalid_openai_key"

        if errors:
            return None, errors, sanitized

        sanitized[CONF_VIKUNJA_URL] = api_url

        if sanitized.get(CONF_ENABLE_USER_ASSIGN):
            await self.hass.async_add_executor_job(
                build_initial_user_cache_sync,
                self.hass.config.config_dir,
                api_url,
                sanitized[CONF_VIKUNJA_API_KEY],
            )

        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=sanitized)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reconfigure_successful"), {}, sanitized

        await self.async_set_unique_id(f"vikunja_{api_url}")
        self._abort_if_unique_id_configured()

        return (
            self.async_create_entry(title=f"Vikunja ({api_url})", data=sanitized),
            {},
            sanitized,
        )

    # Initial configuration step
    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}

        if user_input is not None:
            result, errors, sanitized = await self._async_process_input(user_input)
            if not errors and result is not None:
                return result
            defaults = sanitized

        data_schema = self._build_data_schema(defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    # Reconfiguration step
    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        """Handle reconfiguration of an existing entry."""
        entry: config_entries.ConfigEntry | None = getattr(self, "reconfigure_entry", None)

        if entry is None:
            entry_id = getattr(self, "_reconfigure_entry_id", None) or self.context.get("entry_id")
            if entry_id is not None:
                entry = self.hass.config_entries.async_get_entry(entry_id)

        if entry is None:
            _LOGGER.error("Reconfigure flow started but config entry could not be resolved.")
            return self.async_abort(reason="already_configured")

        self.context.setdefault("title_placeholders", {})
        self.context["title_placeholders"].update({"name": entry.title})

        errors: dict[str, str] = {}
        defaults: dict[str, Any] = dict(entry.data)

        if user_input is not None:
            result, errors, sanitized = await self._async_process_input(
                user_input, existing_entry=entry
            )
            if not errors and result is not None:
                return result
            defaults.update(sanitized)

        data_schema = self._build_data_schema(defaults)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"name": entry.title},
            last_step=True,
        )
