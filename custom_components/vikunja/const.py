DOMAIN = "vikunja"
CONF_VIKUNJA_URL= "vikunja_url"
CONF_VIKUNJA_API_KEY = "vikunja_api_key"
CONF_OPENAI_API_KEY = "openai_api_key"
CONF_DUE_DATE = "default_due_date"
CONF_VOICE_CORRECTION = "voice_correction"
CONF_AUTO_VOICE_LABEL = "auto_voice_label"
CONF_ENABLE_USER_ASSIGN = "enable_user_assignment"
USER_CACHE_FILENAME = "vikunja_users.json"
USER_CACHE_REFRESH_HOURS = 24  # default refresh cadence
DUE_DATE_OPTIONS = [
    "none",
    "tomorrow",
    "end_of_week",
    "end_of_month"
]
DUE_DATE_OPTION_LABELS = {
    "none": "No default",
    "tomorrow": "Tomorrow",
    "end_of_week": "End of week",
    "end_of_month": "End of month",
}

# Response detail configuration
CONF_DETAILED_RESPONSE = "detailed_response"
"""When true, detailed voice responses will include project, labels, due date, assignee, priority and repeat info automatically."""
