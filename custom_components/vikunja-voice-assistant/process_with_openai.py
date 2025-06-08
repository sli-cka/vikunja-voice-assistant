import logging
import json
import aiohttp
from datetime import datetime, timezone
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

# Process with OpenAI, moved outside to be reused
async def process_with_openai(task_description, projects, api_key, model):
    """Process the task with OpenAI API directly."""
    project_names = [{"id": p.get("id"), "name": p.get("title")} for p in projects]
    
    # Get current date and time in ISO format to provide context
    current_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    system_message = {
        "role": "system",
        "content": f"""
        You are an assistant that helps create tasks in Vikunja. 
        Given a task description, you will create a JSON payload for the Vikunja API.
        
        Available projects: {json.dumps(project_names)}
        
        If a project is mentioned in the task description, use its project ID.
        If no project is mentioned, use project ID 1.
        
        CRITICAL TASK FORMATTING INSTRUCTIONS:
        - ALWAYS extract a clear, concise title from the task description
        - The title MUST NOT be empty - this is required
        - If the task is described vaguely, create a reasonable title based on context
        - Move details to the description field
        
        CRITICAL DATE HANDLING INSTRUCTIONS:
        - Current date and time: {current_timestamp}
        - Today's date is: {current_date}
        - When a date or time is mentioned (like "tomorrow", "next week", "Friday", "in 3 days", etc.), calculate the correct future date based on current date above.
        - For the 'due_date' field, use ISO format with timezone: YYYY-MM-DDTHH:MM:SSZ
        - For time-of-day references like "3pm", set the time accordingly; otherwise default to 12:00:00.
        - Always use the future for ambiguous references (e.g., "Friday" should be the next Friday, not a past one)
        - NEVER set due dates in the past - all dates should be future dates.
        - Always include the 'Z' timezone designator at the end of date-time strings.
        
        Output only valid JSON that can be sent to the Vikunja API, with these fields:
        - title (string): The main task title (REQUIRED, MUST NOT BE EMPTY)
        - description (string): Any details about the task
        - project_id (number): The project ID (always required, use 1 if no project specified)
        - due_date (string, optional): The due date if specified, always in format YYYY-MM-DDTHH:MM:SSZ
        
        EXAMPLES:
        Input: "Reminder to pick up groceries tomorrow"
        Output: {{"title": "Pick up groceries", "description": "", "project_id": 1, "due_date": "2023-06-09T12:00:00Z"}}
        
        Input: "I need to finish the report for work by Friday at 5pm"
        Output: {{"title": "Finish work report", "description": "Complete and submit the report", "project_id": 1, "due_date": "2023-06-09T17:00:00Z"}}
        """
    }
    user_message = {
        "role": "user",
        "content": f"Create a task with this description (be sure to include a title): {task_description}"
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
                
                try:
                    # Find JSON in the response if it's wrapped in other text
                    start_idx = raw_response.find('{')
                    end_idx = raw_response.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = raw_response[start_idx:end_idx]
                        # Validate the JSON
                        task_data = json.loads(json_str)
                        
                        # Ensure required fields are present
                        if "title" not in task_data or not task_data["title"]:
                            _LOGGER.error("OpenAI response missing required 'title' field")
                            _LOGGER.debug("Raw OpenAI response: %s", raw_response)
                            return None
                            
                        return json_str
                    else:
                        _LOGGER.error("No JSON found in OpenAI response")
                        _LOGGER.debug("Raw OpenAI response: %s", raw_response)
                        return None
                except (json.JSONDecodeError, ValueError) as err:
                    _LOGGER.error("Failed to parse JSON from OpenAI response: %s", err)
                    _LOGGER.debug("Raw OpenAI response: %s", raw_response)
                    return None
                
    except Exception as err:
        _LOGGER.error("Error processing with OpenAI: %s", err)
        return None