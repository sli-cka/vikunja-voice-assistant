"""Automation for Vikunja Todo AI."""
import logging
import json
import voluptuous as vol
import aiohttp
import asyncio

from homeassistant.core import HomeAssistant, Context, Event, callback
from homeassistant.helpers import intent
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import CONF_URL

from .const import DOMAIN, CONF_API_TOKEN, CONF_OPENAI_API_KEY, CONF_OPENAI_MODEL, DEFAULT_PROJECT_ID
from .vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

# Create a function to set up the automation
async def setup_automation(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Vikunja Todo automation."""
    domain_config = hass.data.get(DOMAIN, {})
    vikunja_url = domain_config.get(CONF_URL)
    api_token = domain_config.get(CONF_API_TOKEN)
    openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
    openai_model = domain_config.get(CONF_OPENAI_MODEL)
    
    if not all([vikunja_url, api_token, openai_api_key]):
        _LOGGER.error("Missing configuration for Vikunja Todo AI automation")
        return False
        
    vikunja_api = VikunjaAPI(vikunja_url, api_token)
    
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
            If no project is mentioned, use project ID 0.
            
            If a date or time is mentioned, add it to the 'due_date' field in ISO format (YYYY-MM-DDTHH:MM:SS).
            
            Output only valid JSON that can be sent to the Vikunja API, with these fields:
            - title (string): The main task title
            - description (string): Any details about the task
            - project_id (number): The project ID (always required, use 1 if no project specified)
            - due_date (string, optional): The due date if specified
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
    hass.bus.async_listen("intent_speech", handle_todo_trigger)
    
    return True