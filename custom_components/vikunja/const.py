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
DEFAULT_PROJECT_ID = 1
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
CONF_RESPONSE_INCLUDE_PROJECT = "response_include_project"
CONF_RESPONSE_INCLUDE_LABELS = "response_include_labels"
CONF_RESPONSE_INCLUDE_DUE_DATE = "response_include_due_date"
CONF_RESPONSE_INCLUDE_ASSIGNEE = "response_include_assignee"