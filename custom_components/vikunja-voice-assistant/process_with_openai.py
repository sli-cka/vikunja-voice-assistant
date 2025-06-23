import logging
import json
import aiohttp
from datetime import datetime, timezone, timedelta
import socket
import asyncio

_LOGGER = logging.getLogger(__name__)

async def process_with_openai(task_description, projects, api_key, model, default_due_date="none", voice_correction=False):
    """Process the task with OpenAI API directly."""
    project_names = [{"id": p.get("id"), "name": p.get("title")} for p in projects]
    
    # Get current date and time in ISO format to provide context
    current_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Calculate default due dates
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=12, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_of_week = (datetime.now(timezone.utc) + timedelta(days=7)).replace(hour=17, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_of_month = (datetime.now(timezone.utc) + timedelta(days=30)).replace(hour=17, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Default due date instructions based on config
    default_due_date_instructions = ""
    if default_due_date != "none":
        default_due_date_value = ""
        if default_due_date == "tomorrow":
            default_due_date_value = tomorrow
        elif default_due_date == "end_of_week":
            default_due_date_value = end_of_week
        elif default_due_date == "end_of_month":
            default_due_date_value = end_of_month
            
        default_due_date_instructions = f"""
        IMPORTANT DEFAULT DUE DATE RULE:
        - If no specific project or due date is mentioned in the task, use this default due date: {default_due_date_value}
        - If a specific project is mentioned, do not set any due date unless the user explicitly mentions one
        - If a specific due date is mentioned by the user, always use that instead of the default
        """
    
    # Add voice correction instructions if enabled
    voice_correction_instructions = ""
    if voice_correction:
        voice_correction_instructions = """
        CRITICAL SPEECH RECOGNITION CORRECTION:
        - The task description came from a voice command that may have speech recognition errors
        - Make informed predictions about what the user actually meant to say, especially for:
          * Project names that might be slightly misspelled or misheard
          * Date/time references that might be unclear or incorrectly transcribed
          * Common speech-to-text errors like "to do" vs "todo", or misheard prepositions
        - Use contextual clues to understand the user's true intent
        - If something seems like a speech recognition error, use your judgment to correct it
        """
    
    system_message = {
        "role": "system",
        "content": f"""
        You are an assistant that helps create tasks in Vikunja. 
        Given a task description, you will create a JSON payload for the Vikunja API.
        
        Available projects: {json.dumps(project_names)}
        
        If a project is mentioned in the task description, use its project ID.
        If no project is mentioned, use project ID 1.
        
        {voice_correction_instructions}
        
        CRITICAL TASK FORMATTING INSTRUCTIONS:
        - ALWAYS extract a clear, concise title from the task description
        - The title MUST NOT be empty - this is required
        - If details are provided, include them in the description field
        
        TASK TITLE OPTIMIZATION:
        - Avoid unnecessary and obvious words that are already implied by the project context
        - For example, if the project is "Groceries", don't include words like "buy", "purchase", or "groceries" in the title
        - Keep titles concise, relevant, and without redundant context already provided by the project
        
        CRITICAL DATE HANDLING INSTRUCTIONS:
        - Current date and time: {current_timestamp}
        - Today's date is: {current_date}
        - When a date or time is mentioned (like "tomorrow", "next week", "Friday", "in 3 days", etc.), calculate the correct future date based on current date above.
        - For the 'due_date' field, use ISO format with timezone: YYYY-MM-DDTHH:MM:SSZ
        - For time-of-day references like "3pm", set the time accordingly; otherwise default to 12:00:00.
        - Always use the future for ambiguous references (e.g., "Friday" should be the next Friday, not a past one)
        - NEVER set due dates in the past - all dates should be future dates.
        - Always include the 'Z' timezone designator at the end of date-time strings.
        - REMOVE date information from the title, it should only be in the 'due_date' field if specified.
        
        {default_due_date_instructions}
        
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
    
    # Define timeouts to prevent hanging
    timeout = aiohttp.ClientTimeout(total=60, connect=15, sock_read=30, sock_connect=15)  # Increased timeouts
    _LOGGER.info(f"Attempting to connect to OpenAI API to process task: '{task_description[:50]}...'")
    
    try:
        # Skip explicit DNS resolution which might be causing timeout issues
        async with aiohttp.ClientSession(timeout=timeout) as session:
            _LOGGER.debug("Sending request to OpenAI API")
            try:
                openai_url = "https://api.openai.com/v1/chat/completions"
                
                async with session.post(
                    openai_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout,
                    ssl=False  # Try disabling SSL verification temporarily to troubleshoot
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error(f"OpenAI API error: {response.status} - {error_text}")
                        return None
                    
                    result = await response.json()
                    _LOGGER.debug("Successfully received response from OpenAI API")
                    
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
                                
                            _LOGGER.info(f"Successfully processed task: '{task_data.get('title', 'Unknown')}'")
                            return json_str
                        else:
                            _LOGGER.error("No JSON found in OpenAI response")
                            _LOGGER.debug("Raw OpenAI response: %s", raw_response)
                            return None
                    except (json.JSONDecodeError, ValueError) as err:
                        _LOGGER.error("Failed to parse JSON from OpenAI response: %s", err)
                        _LOGGER.debug("Raw OpenAI response: %s", raw_response)
                        return None
            
            except asyncio.TimeoutError as timeout_err:
                _LOGGER.error(f"Timeout while connecting to OpenAI API: {timeout_err}")
                return None
            except aiohttp.ClientConnectorError as conn_err:
                _LOGGER.error(f"Connection error to OpenAI API: {conn_err}")
                return None
                
    except aiohttp.ClientError as client_err:
        _LOGGER.error(f"HTTP client error with OpenAI: {client_err}")
        return None
    except asyncio.TimeoutError as timeout_err:
        _LOGGER.error(f"Timeout error with OpenAI: {timeout_err}")
        return None
    except Exception as err:
        _LOGGER.error(f"Error processing with OpenAI: {err}", exc_info=True)
        return None