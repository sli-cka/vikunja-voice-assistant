"""Automation for Vikunja voice assistant."""
import logging
import json
import aiohttp
from typing import Optional

from homeassistant.core import HomeAssistant, Context, Event
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN, 
    CONF_VIKUNJA_API_TOKEN, 
    CONF_OPENAI_API_KEY, 
    CONF_OPENAI_MODEL, 
    CONF_VIKUNJA_URL
)
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

# Create a function to set up the automation
async def setup_automation(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Vikunja voice automation."""
    domain_config = hass.data.get(DOMAIN, {})
    vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
    vikunja_api_token = domain_config.get(CONF_VIKUNJA_API_TOKEN)
    openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
    openai_model = domain_config.get(CONF_OPENAI_MODEL)
    
    if not all([vikunja_url, vikunja_api_token, openai_api_key]):
        _LOGGER.error("Missing configuration for Vikunja voice assistant automation")
        return False
        
    vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_token)
    async def handle_task_trigger(event: Event, context: Optional[Context] = None) -> None:
        """Handle the add task voice trigger."""
        # Extract the voice command
        voice_command = event.data.get("text", "")
        
        if "task" not in voice_command.lower() or "add" not in voice_command.lower():
            _LOGGER.info("Voice command does not match task trigger")
            return
            
        # Remove the "add" and "task" keywords
        task_description = voice_command.lower().replace("add", "").replace("task", "").strip()
        
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
        
    async def process_with_openai(task_description, projects, api_key, model):
        """Process the task with OpenAI API directly."""
        project_names = [{"id": p.get("id"), "name": p.get("title")} for p in projects]
        
        system_message = {
            "role": "system",
            "content": f"""
            You are an assistant that helps create tasks in Vikunja. 
            Given a task description, you will create a JSON payload for the Vikunja API.
            
            Available projects: {json.dumps(project_names)}
            
            If a project is mentioned in the task description, use its project ID.
            If no project is mentioned, use project ID 1.
            
            If a date or time is mentioned, add it to the 'due_date' field in ISO format with timezone (YYYY-MM-DDTHH:MM:SSZ).
            Always include the 'Z' timezone designator at the end of date-time strings.
            
            Output only valid JSON that can be sent to the Vikunja API, with these fields:
            - title (string): The main task title
            - description (string): Any details about the task
            - project_id (number): The project ID (always required, use 1 if no project specified)
            - due_date (string, optional): The due date if specified, always in format YYYY-MM-DDTHH:MM:SSZ
            """
        }
        
        user_message = {
            "role": "user",
            "content": task_description
        }
        
        payload = {
            "model": model,
            "messages": [system_message, user_message],
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error(f"OpenAI API error: {response.status} - {error_text}")
                        return None
                    
                    result = await response.json()
                    
                    # Extract the JSON from the response
                    raw_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
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
                            _LOGGER.error("No JSON found in OpenAI response")
                            return None
                    except (json.JSONDecodeError, ValueError) as err:
                        _LOGGER.error("Failed to parse JSON from OpenAI response: %s", err)
                        return None
                    
        except Exception as err:
            _LOGGER.error("Error processing with OpenAI: %s", err)
            return None
            
    # Subscribe to the intent recognition event
    hass.bus.async_listen("intent_speech", handle_task_trigger)
    hass.bus.async_listen("conversation_processing", handle_task_trigger)
    
    return True