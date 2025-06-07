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
            response = requests.get(projects_url, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Connection test failed: %s", err)
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
            return None