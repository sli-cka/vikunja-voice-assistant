import logging
import requests
import json

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

    def create_label(self, label_data):
        """Create a new label in Vikunja."""
        labels_url = f"{self.url}/labels"
        
        # Validate required fields
        if not label_data.get("title"):
            _LOGGER.error("Cannot create label: missing 'title' field in label data")
            return None
        
        try:
            _LOGGER.debug("Creating label with data: %s", json.dumps(label_data))
            response = requests.put(labels_url, headers=self.headers, json=label_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create label: %s", err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return None

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