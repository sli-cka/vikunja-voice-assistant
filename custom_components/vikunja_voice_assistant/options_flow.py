import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_AI_TASK_ENTITY,
    CONF_DUE_DATE,
    DUE_DATE_OPTIONS,
    CONF_VOICE_CORRECTION,
    CONF_AUTO_VOICE_LABEL,
    CONF_ENABLE_USER_ASSIGN,
    DUE_DATE_OPTION_LABELS,
    CONF_DETAILED_RESPONSE,
)
from .helpers.localization import get_language
from .user_cache import build_initial_user_cache_sync

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle options flow for Vikunja Voice Assistant."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Handle user cache refresh if user assignment was toggled on
            if user_input.get(CONF_ENABLE_USER_ASSIGN):
                try:
                    await self.hass.async_add_executor_job(
                        build_initial_user_cache_sync,
                        self.hass.config.config_dir,
                        self.config_entry.data["vikunja_url"],
                        self.config_entry.data["vikunja_api_key"],
                    )
                except Exception as err:
                    _LOGGER.error("Failed to build user cache: %s", err)

            return self.async_create_entry(title="", data=user_input)

        # Get current values from options (or fall back to data for migration)
        current_options = {
            CONF_AI_TASK_ENTITY: self.config_entry.options.get(
                CONF_AI_TASK_ENTITY,
                self.config_entry.data.get(CONF_AI_TASK_ENTITY, ""),
            ),
            CONF_VOICE_CORRECTION: self.config_entry.options.get(
                CONF_VOICE_CORRECTION,
                self.config_entry.data.get(CONF_VOICE_CORRECTION, True),
            ),
            CONF_AUTO_VOICE_LABEL: self.config_entry.options.get(
                CONF_AUTO_VOICE_LABEL,
                self.config_entry.data.get(CONF_AUTO_VOICE_LABEL, True),
            ),
            CONF_ENABLE_USER_ASSIGN: self.config_entry.options.get(
                CONF_ENABLE_USER_ASSIGN,
                self.config_entry.data.get(CONF_ENABLE_USER_ASSIGN, False),
            ),
            CONF_DUE_DATE: self.config_entry.options.get(
                CONF_DUE_DATE, self.config_entry.data.get(CONF_DUE_DATE, "tomorrow")
            ),
            CONF_DETAILED_RESPONSE: self.config_entry.options.get(
                CONF_DETAILED_RESPONSE,
                self.config_entry.data.get(CONF_DETAILED_RESPONSE, True),
            ),
        }

        lang = get_language(self.hass)
        due_date_selector = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(
                        value=value,
                        label=(
                            DUE_DATE_OPTION_LABELS.get(value, {}).get(lang)
                            or DUE_DATE_OPTION_LABELS.get(value, {}).get("en", value)
                        ),
                    )
                    for value in DUE_DATE_OPTIONS
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
        ai_task_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["ai_task"],
            )
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_AI_TASK_ENTITY,
                    default=current_options[CONF_AI_TASK_ENTITY],
                ): ai_task_selector,
                vol.Required(
                    CONF_VOICE_CORRECTION,
                    default=current_options[CONF_VOICE_CORRECTION],
                ): cv.boolean,
                vol.Required(
                    CONF_AUTO_VOICE_LABEL,
                    default=current_options[CONF_AUTO_VOICE_LABEL],
                ): cv.boolean,
                vol.Required(
                    CONF_ENABLE_USER_ASSIGN,
                    default=current_options[CONF_ENABLE_USER_ASSIGN],
                ): cv.boolean,
                vol.Required(
                    CONF_DUE_DATE, default=current_options[CONF_DUE_DATE]
                ): due_date_selector,
                vol.Required(
                    CONF_DETAILED_RESPONSE,
                    default=current_options[CONF_DETAILED_RESPONSE],
                ): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )