"""Vikunja API helper."""
import logging
import requests
import json

_LOGGER = logging.getLogger(__name__)

class VikunjaAPI:
    """Class to handle Vikunja API calls."""

    def __init__(self, url, api_token):
        """Initialize the API client."""
        self.url = url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}"
        }
        
    def test_connection(self):
        """Test the connection to Vikunja API."""
        projects_url = f"{self.url}/projects"
        
        try:
            _LOGGER.debug("Testing connection to %s with token: %s...", projects_url, self.api_token[:5] + "...")
            response = requests.get(projects_url, headers=self.headers)
            
            # Log more details about the request and response
            _LOGGER.debug("Request headers: %s", self.headers)
            _LOGGER.debug("Response status: %s", response.status_code)
            _LOGGER.debug("Response body: %s", response.text[:100] + "..." if len(response.text) > 100 else response.text)
            
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Connection test failed: %s", err)
            # Additional debug info
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return False
            
    def get_projects(self):
        """Get all projects from Vikunja."""
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
            
    def add_task(self, task_data):
        """Add a task to Vikunja."""
        tasks_url = f"{self.url}/tasks"
        
        try:
            response = requests.post(tasks_url, headers=self.headers, json=task_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create task: %s", err)
            if hasattr(err, 'response') and err.response is not None:
                _LOGGER.error("Response content: %s", err.response.text)
            return None