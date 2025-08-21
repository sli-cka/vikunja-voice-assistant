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
        """Simple connectivity check by listing projects."""
        try:
            response = requests.get(f"{self.url}/projects", headers=self.headers, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Connection test failed: %s", err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return False
            
    def get_projects(self):
        try:
            response = requests.get(f"{self.url}/projects", headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to get projects: %s", err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return []

    def get_labels(self):
        try:
            response = requests.get(f"{self.url}/labels", headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to get labels: %s", err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return []

    def create_label(self, label_name):
        """Create a new label with a random hex color."""
        payload = {"title": label_name, "hex_color": secrets.token_hex(3)}
        try:
            response = requests.put(f"{self.url}/labels", headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create label '%s': %s", label_name, err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return None

    def add_label_to_task(self, task_id: int, label_id: int):
        """Attach existing label to a task. Returns True on success."""
        try:
            response = requests.put(
                f"{self.url}/tasks/{task_id}/labels",
                headers=self.headers,
                json={"label_id": label_id},
                timeout=30,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to attach label %s to task %s: %s", label_id, task_id, err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return False

    def add_task(self, task_data):
        """Create a new task (requires title, uses project_id then removes it)."""
        project_id = task_data.get("project_id", 1)
        task_data.pop("project_id", None)
        if not task_data.get("title"):
            _LOGGER.error("Cannot create task: missing 'title'")
            return None
        try:
            response = requests.put(
                f"{self.url}/projects/{project_id}/tasks",
                headers=self.headers,
                json=task_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to create task in project %s: %s", project_id, err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return None