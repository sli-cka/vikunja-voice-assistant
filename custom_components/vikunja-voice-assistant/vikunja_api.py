import logging
import requests
import json
import secrets

_LOGGER = logging.getLogger(__name__)

class VikunjaAPI:
    def __init__(self, url, vikunja_api_token):
        self.url = url.rstrip('/')
        self.api_token = vikunja_api_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {vikunja_api_token}"
        }
        
    def test_connection(self):
    
        projects_url = f"{self.url}/projects"
        
        try:
            response = requests.get(projects_url, headers=self.headers)
            
            # Log more details about the request and response
            
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Connection test failed: %s", err)
            # Additional debug info
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return False
            
    def get_projects(self):
    
        projects_url = f"{self.url}/projects"
        
        try:
            response = requests.get(projects_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to get projects: %s", err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return []

    def get_labels(self):
        labels_url = f"{self.url}/labels"
        
        try:
            response = requests.get(labels_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to get labels: %s", err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return []

    def create_label(self, label_name):
        """Create a new label in Vikunja."""
        labels_url = f"{self.url}/labels"
        hex_color = secrets.token_hex(3)  # 
        payload = {"name": label_name, "hex_color": hex_color}
        
        try:
            response = requests.put(labels_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create label '%s': %s", label_name, err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return None

    def add_label_to_task(self, task_id: int, label_id: int):
        """Attach an existing label to a task via PUT /tasks/{task}/labels.

        Returns True on success, False otherwise.
        """
        url = f"{self.url}/tasks/{task_id}/labels"
        payload = {"label_id": label_id}
        try:
            response = requests.put(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to attach label %s to task %s: %s", label_id, task_id, err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return False

    def add_task(self, task_data):
        """Create a new task in a Vikunja project."""
        project_id = task_data.get("project_id", 1)
        
        if "project_id" in task_data:
            del task_data["project_id"]
        
        # Validate required fields
        if not task_data.get("title"):
            _LOGGER.error("Cannot create task: missing 'title' field in task data")
            return None
                
        tasks_url = f"{self.url}/projects/{project_id}/tasks"
        
        _LOGGER.debug("Adding task to project %s with data: %s", project_id, json.dumps(task_data)) 
        try:
            _LOGGER.debug("Creating task in project %s with data: %s", project_id, json.dumps(task_data))
            response = requests.put(tasks_url, headers=self.headers, json=task_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create task in project %s: %s", project_id, err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return None