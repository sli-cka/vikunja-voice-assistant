"""Vikunja API helper."""
import logging
import requests
import json

_LOGGER = logging.getLogger(__name__)

class VikunjaAPI:
    """Class to handle Vikunja API calls."""

    def __init__(self, url, username, password):
        """Initialize the API client."""
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.headers = {"Content-Type": "application/json"}
        
    def authenticate(self):
        """Authenticate with Vikunja API and get token."""
        auth_url = f"{self.url}/login"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(auth_url, json=payload)
            response.raise_for_status()
            self.token = response.json().get("token")
            self.headers["Authorization"] = f"Bearer {self.token}"
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Authentication failed: %s", err)
            return False
            
    def get_projects(self):
        """Get all projects from Vikunja."""
        if not self.token:
            if not self.authenticate():
                return []
                
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
        if not self.token:
            if not self.authenticate():
                return False
                
        tasks_url = f"{self.url}/tasks"
        
        try:
            response = requests.post(tasks_url, headers=self.headers, json=task_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create task: %s", err)
            return None
