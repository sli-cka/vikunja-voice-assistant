import logging
import json
import requests
from datetime import datetime, timezone, timedelta
import socket

_LOGGER = logging.getLogger(__name__)

def process_with_openai(task_description, projects, api_key,  default_due_date="none", voice_correction=False):
    """Process the task with OpenAI API using a synchronous requests call.

    This function is synchronous by design so it must be run in an executor
    when called from Home Assistant's event loop.
    """
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
        - Even if a recurring task instruction is given, if no due date is mentioned, set it to {default_due_date_value}
        """
    
    # Add voice correction instructions if enabled
    voice_correction_instructions = ""
    if voice_correction:
        voice_correction_instructions = """
        SPEECH RECOGNITION CORRECTION:
        - Task came from voice command - expect speech recognition errors
        - Correct misheard project names, dates, and common speech-to-text errors
        - Use context to understand user's true intent
        """

    
        system_message = {
                "role": "system",
                "content": f"""
                You are an assistant that helps create tasks in Vikunja. 
                Given a task description, you will create a JSON payload for the Vikunja API.
        
                Available projects: {json.dumps(project_names)}
        
                DEFAULT DUE DATE RULE:
                {default_due_date_instructions.strip() if default_due_date_instructions else "- No default due date configured"}
        
                {voice_correction_instructions.strip() if voice_correction_instructions else ""}
        
                CORE OUTPUT REQUIREMENTS:
                - Output only valid JSON with these fields (only include optional fields when applicable):
                    * title (string): Main task title (REQUIRED, MUST NOT BE EMPTY)
                    * description (string): Secondary / extended details ONLY when needed. Use empty string otherwise.
                    * project_id (number): Project ID (always required, use 1 if no project specified)
                    * due_date (string, optional): Due date in YYYY-MM-DDTHH:MM:SSZ format
                    * priority (number, optional): Priority level 1-5, only when explicitly mentioned
                    * repeat_after (number, optional): Repeat interval in seconds, only for recurring tasks
                    * label_ids (array, optional): Array of existing label IDs to assign to task
        
                TITLE VS DESCRIPTION RULES:
                - Put ALL essential task info in the title whenever it reasonably fits (roughly up to two short lines ~160 chars)
                - Use description ONLY for clearly secondary info: background context, rationale, optional notes, long instructions
                - Do NOT move essential info (action, objects, key qualifiers, due context) out of the title just to shorten it
                - If the task is simple/concise, leave description as an empty string
                - If description would just repeat title content, leave it empty
        
                TASK FORMATTING:
                - Extract clear, concise titles
                - Avoid redundant words implied by project context
                - Remove date/time info from title (use due_date field)
                - Remove label references from title (handled via label_ids)
                - Remove project names from title (handled via project_id)
                - Remove priority references from title (handled via priority field)
                - Remove unnecessary qualifiers (e.g. "task", "to do", "reminder")
                - Remove recurring task keywords from title (handled via repeat_after)

                DATE HANDLING (Current: {current_timestamp}):
                - Calculate future dates based on current date: {current_date}
                - Use ISO format with 'Z' timezone: YYYY-MM-DDTHH:MM:SSZ
                - Default time: 12:00:00 (unless specific time mentioned)
                - NEVER set past dates - always use future dates for ambiguous references

                PRIORITY LEVELS (only when explicitly mentioned):
                - 5: urgent, critical, emergency, ASAP, immediately
                - 4: important, soon, priority, needs attention
                - 3: medium priority, when possible, moderately important
                - 2: low priority, when you have time, not urgent
                - 1: sometime, eventually, no rush
        
                RECURRING TASKS (only when explicitly mentioned):
                - Daily: 86400 seconds | Weekly: 604800 seconds
                - Monthly: 2592000 seconds | Yearly: 31536000 seconds
                - Keywords: daily, weekly, monthly, yearly, every day/week, recurring, repeat...
        
                EXAMPLES:
                Input: "Reminder to pick up groceries tomorrow"
                Output: {{"title": "Pick up groceries", "description": "", "project_id": 1, "due_date": "2023-06-09T12:00:00Z"}}
        
                Input: "URGENT: I need to finish the report for work by Friday at 5pm tagged as urgent"
                Output: {{"title": "Finish work report", "description": "", "project_id": 1, "due_date": "2023-06-09T17:00:00Z", "priority": 5}}
        
                Input: "Prepare quarterly financial analysis with notes: include variance vs last year and highlight risks"
                Output: {{"title": "Prepare quarterly financial analysis", "description": "Include variance vs last year and highlight risks", "project_id": 1, "due_date": "default due date provided above"}}
        
                Input: "Take vitamins daily with health"
                Output: {{"title": "Take vitamins", "description": "", "project_id": 1, "repeat_after": 86400, due_date": "default due date provided above"}}

                Input: "Debug the voice assistant project to the computer project"
                Output: {{"title": "Debug the voice assistant project", "description": "", "project_id": 2"}}
                """
        }
    
    user_message = {
        "role": "user",
        "content": f"Create task: {task_description}"
    }
    payload = {
        "model": 'gpt-5-mini',
        "messages": [system_message, user_message],
        "reasoning_effort": "minimal"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    _LOGGER.info(f"Attempting to connect to OpenAI API to process task: '{task_description[:50]}...'")
    
    try:
        _LOGGER.debug("Sending request to OpenAI API (sync call)")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        
        if response.status_code != 200:
            _LOGGER.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
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

                return json.dumps({
                    "task_data": task_data,
                })
            else:
                _LOGGER.error("No JSON found in OpenAI response")
                _LOGGER.debug("Raw OpenAI response: %s", raw_response)
                return None
        except (json.JSONDecodeError, ValueError) as err:
            _LOGGER.error("Failed to parse JSON from OpenAI response: %s", err)
            _LOGGER.debug("Raw OpenAI response: %s", raw_response)
            return None
                
    except requests.exceptions.Timeout as timeout_err:
        _LOGGER.error(f"Timeout while connecting to OpenAI API: {timeout_err}")
        return None
    except requests.exceptions.ConnectionError as conn_err:
        _LOGGER.error(f"Connection error to OpenAI API: {conn_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        _LOGGER.error(f"Request error with OpenAI: {req_err}")
        return None
    except Exception as err:
        _LOGGER.error(f"Error processing with OpenAI: {err}", exc_info=True)
        return None