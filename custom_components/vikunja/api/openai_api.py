import logging
import json
import requests

from ..helpers.prompt_builder import build_task_creation_messages

_LOGGER = logging.getLogger(__name__)


class OpenAIAPI:
    def __init__(self, api_key: str, model: str = "gpt-5-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def _post(self, path: str, payload: dict, timeout: int = 60):
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                headers=self.headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as err:  # noqa: BLE001
            _LOGGER.error("OpenAI request failed: %s", err)
            resp = getattr(err, "response", None)
            if resp is not None and hasattr(resp, "text"):
                _LOGGER.error("Response content: %s", resp.text)
            return None

    def create_task_from_description(
        self,
        task_description: str,
        projects,
        labels,
        default_due_date: str = "none",
        voice_correction: bool = False,
        reasoning_effort: str = "minimal",
        users=None,
        enable_user_assignment: bool = False,
    ):
        messages = build_task_creation_messages(
            task_description,
            projects,
            labels,
            default_due_date,
            voice_correction,
            users,
            enable_user_assignment,
        )

        payload = {
            "model": self.model,
            "messages": messages,
            "reasoning_effort": reasoning_effort,
        }

        _LOGGER.info("Processing task via OpenAI: '%s'", task_description[:50])
        response = self._post("/chat/completions", payload)
        if response is None:
            return None

        try:
            result = response.json()
            raw_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Extract JSON content
            start_idx = raw_response.find("{")
            end_idx = raw_response.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = raw_response[start_idx:end_idx]
                task_data = json.loads(json_str)
                if "title" not in task_data or not task_data["title"]:
                    _LOGGER.error("OpenAI response missing required 'title' field")
                    return None
                _LOGGER.info("Successfully processed task: '%s'", task_data.get("title", "Unknown"))
                return {"task_data": task_data}
            _LOGGER.error("No JSON found in OpenAI response")
            return None
        except (json.JSONDecodeError, ValueError) as err:  # noqa: BLE001
            _LOGGER.error("Failed to parse JSON from OpenAI response: %s", err)
            return None
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unexpected error handling OpenAI response: %s", err)
            return None
