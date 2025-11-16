from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant

from ..helpers.prompt_builder import build_task_creation_messages

_LOGGER = logging.getLogger(__name__)


class HomeAssistantLLMAPI:
    """Interface to Home Assistant's AI task pipeline."""

    _DEFAULT_TASK_NAME = "Generate Vikunja task"

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        """Store Home Assistant instance and target AI task entity."""
        self._hass = hass
        self._entity_id = entity_id.strip()

    async def create_task_from_description(
        self,
        task_description: str,
        projects: Optional[List[Dict[str, Any]]],
        labels: Optional[List[Dict[str, Any]]],
        default_due_date: str = "none",
        voice_correction: bool = False,
        users: Optional[List[Dict[str, Any]]] = None,
        enable_user_assignment: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Use HA's LLM pipeline to transform a natural language description into task data."""
        if not self._entity_id:
            _LOGGER.error("No AI Task entity configured for Vikunja voice assistant")
            return None

        messages = build_task_creation_messages(
            task_description,
            projects,
            labels,
            default_due_date,
            voice_correction,
            users,
            enable_user_assignment,
        )
        prompt = self._format_messages_to_prompt(messages)

        request_payload: Dict[str, Any] = {
            "entity_id": self._entity_id,
            "task_name": self._derive_task_name(task_description),
            "instructions": prompt,
        }

        try:
            response = await self._hass.services.async_call(
                "ai_task",
                "generate_data",
                request_payload,
                blocking=True,
                return_response=True,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("LLM service call failed: %s", err)
            return None

        if not response:
            _LOGGER.error("Empty response from Home Assistant LLM service")
            return None

        task_data = self._parse_llm_response(response)
        if task_data is None:
            _LOGGER.error("Failed to extract structured task data from LLM response")
            return None

        _LOGGER.info(
            "Successfully processed task via Home Assistant AI Task: '%s'",
            task_data.get("title", "Unknown"),
        )
        return {"task_data": task_data}

    def _parse_llm_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract structured task data from ai_task.generate_data response."""
        if not response:
            return None

        response_block = response.get("response")
        data_block = response.get("data")

        # Some providers may already supply structured data.
        if isinstance(data_block, dict):
            parsed = data_block.get("parsed")
            if isinstance(parsed, dict):
                return self._validate_task_data(parsed)

        candidates: List[str] = []

        if isinstance(response_block, dict):
            for field in ("markdown", "plain", "spoken"):
                value = response_block.get(field)
                if isinstance(value, str):
                    candidates.append(value)
        elif isinstance(response_block, str):
            candidates.append(response_block)

        if isinstance(data_block, dict):
            content = data_block.get("content")
            if isinstance(content, str):
                candidates.append(content)
        elif isinstance(data_block, str):
            candidates.append(data_block)

        for candidate in candidates:
            task_data = self._extract_json(candidate)
            if task_data is not None:
                return self._validate_task_data(task_data)

        return None

    def _validate_task_data(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform minimal validation on parsed JSON payload."""
        if not isinstance(task_data, dict):
            return None
        if not task_data.get("title"):
            _LOGGER.error("LLM response missing required 'title' field")
            return None
        return task_data

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Locate and decode the first JSON object within the provided text."""
        if not text:
            return None
        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1
        if start_idx < 0 or end_idx <= start_idx:
            return None

        json_str = text[start_idx:end_idx]
        try:
            decoded = json.loads(json_str)
        except json.JSONDecodeError:
            _LOGGER.debug("Failed to decode JSON candidate from LLM output")
            return None

        if not isinstance(decoded, dict):
            return None
        return decoded

    def _derive_task_name(self, task_description: str) -> str:
        """Derive a concise task name for the AI Task request."""
        if not task_description:
            return self._DEFAULT_TASK_NAME
        collapsed = " ".join(task_description.split())
        if not collapsed:
            return self._DEFAULT_TASK_NAME
        return collapsed[:120]

    def _format_messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert chat-style messages into a single prompt string."""
        segments: List[str] = []
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            if not isinstance(content, str) or not content:
                continue
            prefix = ""
            if role == "system":
                prefix = "System"
            elif role == "assistant":
                prefix = "Assistant"
            else:
                prefix = "User"
            segments.append(f"{prefix}: {content}")
        return "\n\n".join(segments)