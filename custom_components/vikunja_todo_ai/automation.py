"""Automation for Vikunja Todo AI."""
import logging
import json
import voluptuous as vol

from homeassistant.components.automation import AutomationActionType
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant, Context, Event
from homeassistant.helpers import intent
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_OPENAI_CONVERSATION, DEFAULT_PROJECT_ID
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

async def async_get_automations(hass: HomeAssistant, config: ConfigType) -> list[dict]:
    """Return all automations for this platform."""
    return [vikunja_todo_automation]

async def vikunja_todo_automation(hass: HomeAssistant, config: ConfigType) -> AutomationActionType:
    """Create an automation for handling todo voice commands."""
    
    domain_config = hass.data.get(DOMAIN, {})
    vikunja_url = domain_config.get(CONF_URL)
    username = domain_config.get(CONF_USERNAME)
    password = domain_config.get(CONF_PASSWORD)
    openai_conversation = domain_config.get(CONF_OPENAI_CONVERSATION)
    
    if not all([vikunja_url, username, password, openai_conversation]):
        _LOGGER.error("Missing configuration for Vikunja Todo AI")
        return None
        
    vikunja_api = VikunjaAPI(vikunja_url, username, password)
    
    async def handle_todo_trigger(event: Event, context: Context = None) -> None:
        """Handle the todo voice trigger."""
        # Extract the voice command
        voice_command = event.data.get("text", "")
        
        if not voice_command.lower().startswith("todo"):
            return
            
        # Remove the "todo" keyword
        task_description = voice_command[4:].strip(": ")
        
        # Get all projects from Vikunja
        projects = await hass.async_add_executor_job(vikunja_api.get_projects)
        
        # Process with OpenAI
        openai_response = await process_with_openai(hass, task_description, projects, openai_conversation)
        
        if not openai_response:
            _LOGGER.error("Failed to process with OpenAI")
            return
            
        # Send request to Vikunja
        await hass.async_add_executor_job(
            lambda: vikunja_api.add_task(json.loads(openai_response))
        )
        
    async def process_with_openai(hass, task_description, projects, openai_conversation_id):
        """Process the task with OpenAI."""
        project_names = [{"id": p.get("id"), "name": p.get("title")} for p in projects]
        
        # Create system prompt with project info
        system_prompt = f"""
        You are an assistant that helps create tasks in Vikunja. 
        Given a task description, you will create a JSON payload for the Vikunja API.
        
        Available projects: {json.dumps(project_names)}
        
        If a project is mentioned in the task description, use its project ID.
        If no project is mentioned, use project ID {DEFAULT_PROJECT_ID}.
        
        If a date or time is mentioned, add it to the 'due_date' field in ISO format (YYYY-MM-DDTHH:MM:SS).
        
        Output only valid JSON that can be sent to the Vikunja API, with these fields:
        - title (string): The main task title
        - description (string): Any details about the task
        - project_id (number): The project ID
        - due_date (string, optional): The due date if specified
        """
        
        try:
            # Call the OpenAI conversation
            response = await hass.services.async_call(
                "conversation",
                "process",
                {
                    "text": task_description,
                    "agent_id": openai_conversation_id,
                    "prompt": system_prompt
                },
                blocking=True,
                return_response=True
            )
            
            # Extract the JSON from the response
            raw_response = response.get("response", {}).get("speech", {})
            
            # Clean up the response to extract just the JSON part
            try:
                # Find JSON in the response if it's wrapped in other text
                start_idx = raw_response.find('{')
                end_idx = raw_response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = raw_response[start_idx:end_idx]
                    # Validate the JSON
                    json.loads(json_str)
                    return json_str
                else:
                    return None
            except (json.JSONDecodeError, ValueError) as err:
                _LOGGER.error("Failed to parse JSON from OpenAI response: %s", err)
                return None
                
        except Exception as err:
            _LOGGER.error("Error processing with OpenAI: %s", err)
            return None
            
    # Subscribe to the intent recognition event
    hass.bus.async_listen("intent_speech", handle_todo_trigger)
    
    return {"trigger_todo": handle_todo_trigger}
