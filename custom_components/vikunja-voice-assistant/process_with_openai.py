import logging
import json
import requests
from datetime import datetime, timezone, timedelta
import socket
import asyncio

_LOGGER = logging.getLogger(__name__)

async def check_and_create_labels(task_description, labels, api_key, model, voice_correction=False):
    """Check if labels are mentioned and create them if needed."""
    label_names = [{"id": l.get("id"), "name": l.get("title")} for l in labels]
    
    voice_correction_instructions = ""
    if voice_correction:
        voice_correction_instructions = """
        SPEECH RECOGNITION CORRECTION:
        - Task came from voice command - expect speech recognition errors
        - Correct misheard label names and common speech-to-text errors
        - Use context to understand user's true intent for label names
        """
    
    system_message = {
        "role": "system",
        "content": f"""
        You are an assistant that identifies labels mentioned in task descriptions.
        
        Available labels: {json.dumps(label_names)}
        
        {voice_correction_instructions.strip() if voice_correction_instructions else ""}
        
        LABEL DETECTION RULES:
        - Look for words that indicate labels: "label", "tag", "category", "type", "mark as", "tagged", etc.
        - Also detect context-based labels like urgency levels, categories, or descriptive tags
        - Match existing labels by name (case-insensitive, fuzzy matching for speech errors)
        - If a mentioned label doesn't exist, suggest creating it
        
        OUTPUT REQUIREMENTS:
        - Output only valid JSON with this structure:
        {{
          "mentioned_labels": [
            {{"name": "existing_label_name", "id": 123, "action": "use"}},
            {{"name": "new_label_name", "action": "create"}}
          ]
        }}
        
        EXAMPLES:
        Input: "Add task to label urgent finish the report"
        Output: {{"mentioned_labels": [{{"name": "urgent", "action": "create"}}]}}
        
        Input: "Create task tagged as work meeting with client"
        Output: {{"mentioned_labels": [{{"name": "work", "id": 1, "action": "use"}}]}}
        
        Input: "Add task buy groceries" (no labels mentioned)
        Output: {{"mentioned_labels": []}}
        """
    }
    
    user_message = {
        "role": "user",
        "content": f"Identify any labels mentioned in this task description: {task_description}"
    }
    
    payload = {
        "model": model,
        "messages": [system_message, user_message],
        "temperature": 0.3
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        # Make the request in a separate thread
        response = await asyncio.to_thread(
            requests.post,
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            _LOGGER.error(f"OpenAI API error for label detection: {response.status_code} - {response.text}")
            return []
        
        result = response.json()
        raw_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        try:
            start_idx = raw_response.find('{')
            end_idx = raw_response.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = raw_response[start_idx:end_idx]
                label_data = json.loads(json_str)
                return label_data.get("mentioned_labels", [])
            else:
                _LOGGER.warning("No JSON found in label detection response")
                return []
        except (json.JSONDecodeError, ValueError) as err:
            _LOGGER.error("Failed to parse JSON from label detection response: %s", err)
            return []
                    
    except Exception as err:
        _LOGGER.error(f"Error checking labels with OpenAI: {err}")
        return []

async def process_with_openai(task_description, projects, labels, api_key, model, default_due_date="none", voice_correction=False):
    """Process the task with OpenAI API directly."""
    project_names = [{"id": p.get("id"), "name": p.get("title")} for p in projects]
    
    # First, check for labels and create them if needed
    mentioned_labels = await check_and_create_labels(task_description, labels, api_key, model, voice_correction)
    processed_labels = []
    
    # This will be populated with actual label creation if needed
    # For now, we'll process the mentioned labels
    for label_info in mentioned_labels:
        if label_info.get("action") == "use":
            processed_labels.append({"id": label_info["id"], "name": label_info["name"]})
        elif label_info.get("action") == "create":
            # We'll need to create this label - for now, add it to the list with a placeholder
            processed_labels.append({"name": label_info["name"], "needs_creation": True})
    
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
    
    # Include label information in the system message
    label_instructions = ""
    if processed_labels:
        label_instructions = f"""
        LABEL HANDLING:
        - These labels were identified for this task: {json.dumps(processed_labels)}
        - Include label_ids array in output with the IDs of existing labels
        - For labels that need creation, include labels_to_create array with label names
        """
    
    system_message = {
        "role": "system",
        "content": f"""
        You are an assistant that helps create tasks in Vikunja. 
        Given a task description, you will create a JSON payload for the Vikunja API.
        
        Available projects: {json.dumps(project_names)}
        Available labels: {json.dumps([{"id": l.get("id"), "name": l.get("title")} for l in labels])}
        
        DEFAULT DUE DATE RULE:
        {default_due_date_instructions.strip() if default_due_date_instructions else "- No default due date configured"}
        
        {voice_correction_instructions.strip() if voice_correction_instructions else ""}
        
        {label_instructions.strip() if label_instructions else ""}
        
        CORE OUTPUT REQUIREMENTS:
        - Output only valid JSON with these fields (only include optional fields when applicable):
          * title (string): Main task title (REQUIRED, MUST NOT BE EMPTY)
          * description (string): Task details (always include, use empty string if none)
          * project_id (number): Project ID (always required, use 1 if no project specified)
          * due_date (string, optional): Due date in YYYY-MM-DDTHH:MM:SSZ format
          * priority (number, optional): Priority level 1-5, only when explicitly mentioned
          * repeat_after (number, optional): Repeat interval in seconds, only for recurring tasks
          * label_ids (array, optional): Array of existing label IDs to assign to task
          * labels_to_create (array, optional): Array of label names that need to be created
        
        TASK FORMATTING:
        - Extract clear, concise titles from task descriptions
        - Avoid redundant words already implied by project context
        - Remove date/time information from titles (put in due_date field instead)
        - Remove label references from titles (handle in label_ids field)
        - Include relevant details in description field
        
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
        - Keywords: daily, weekly, monthly, yearly, every day/week, recurring, repeat
        
        EXAMPLES:
        Input: "Reminder to pick up groceries tomorrow"
        Output: {{"title": "Pick up groceries", "description": "", "project_id": 1, "due_date": "2023-06-09T12:00:00Z"}}
        
        Input: "URGENT: I need to finish the report for work by Friday at 5pm tagged as urgent"
        Output: {{"title": "Finish work report", "description": "Complete and submit the report", "project_id": 1, "due_date": "2023-06-09T17:00:00Z", "priority": 5, "labels_to_create": ["urgent"]}}
        
        Input: "Take vitamins daily with health label"
        Output: {{"title": "Take vitamins", "description": "", "project_id": 1, "repeat_after": 86400, "labels_to_create": ["health"]}}
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
    
    _LOGGER.info(f"Attempting to connect to OpenAI API to process task: '{task_description[:50]}...'")
    
    try:
        _LOGGER.debug("Sending request to OpenAI API")
        
        # Make the request in a separate thread
        response = await asyncio.to_thread(
            requests.post,
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
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
                
                # Return the task data with label information
                return json.dumps({
                    "task_data": task_data,
                    "labels_to_create": task_data.get("labels_to_create", [])
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