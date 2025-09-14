"""Core task processing logic extracted from __init__ for clarity."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Tuple

from .const import (
    DOMAIN,
    CONF_VIKUNJA_URL,
    CONF_VIKUNJA_API_KEY,
    CONF_OPENAI_API_KEY,
    CONF_DUE_DATE,
    CONF_VOICE_CORRECTION,
    CONF_AUTO_VOICE_LABEL,
    CONF_ENABLE_USER_ASSIGN,
    CONF_DETAILED_RESPONSE,
    CONF_RESPONSE_INCLUDE_PROJECT,
    CONF_RESPONSE_INCLUDE_LABELS,
    CONF_RESPONSE_INCLUDE_DUE_DATE,
    CONF_RESPONSE_INCLUDE_ASSIGNEE,
)
from .vikunja_api import VikunjaAPI
from .openai_api import OpenAIAPI

_LOGGER = logging.getLogger(__name__)


async def process_task(hass, task_description: str, user_cache_users: List[Dict[str, Any]]):
    """Create a Vikunja task from natural language description.

    Returns (success, message, task_title)
    """
    domain_config = hass.data.get(DOMAIN, {})
    vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
    vikunja_api_key = domain_config.get(CONF_VIKUNJA_API_KEY)
    openai_api_key = domain_config.get(CONF_OPENAI_API_KEY)
    default_due_date = domain_config.get(CONF_DUE_DATE, "none")
    voice_correction = domain_config.get(CONF_VOICE_CORRECTION, True)
    auto_voice_label = domain_config.get(CONF_AUTO_VOICE_LABEL, True)
    enable_user_assignment = domain_config.get(CONF_ENABLE_USER_ASSIGN, False)
    detailed_response = domain_config.get(CONF_DETAILED_RESPONSE, False)
    include_project = domain_config.get(CONF_RESPONSE_INCLUDE_PROJECT, True)
    include_labels = domain_config.get(CONF_RESPONSE_INCLUDE_LABELS, True)
    include_due_date = domain_config.get(CONF_RESPONSE_INCLUDE_DUE_DATE, True)
    include_assignee = domain_config.get(CONF_RESPONSE_INCLUDE_ASSIGNEE, True)

    if not all([vikunja_url, vikunja_api_key, openai_api_key]):
        _LOGGER.error("Missing configuration for Vikunja voice assistant")
        return False, "Configuration error. Please check your Vikunja and OpenAI settings.", ""

    vikunja_api = VikunjaAPI(vikunja_url, vikunja_api_key)
    projects, labels = await asyncio.gather(
        hass.async_add_executor_job(vikunja_api.get_projects),
        hass.async_add_executor_job(vikunja_api.get_labels),
    )

    voice_label_id = None
    if auto_voice_label:
        try:
            for lbl in labels or []:
                if isinstance(lbl, dict) and lbl.get("title", "").lower() == "voice":
                    voice_label_id = lbl.get("id")
                    break
            if voice_label_id is None:
                voice_label = await hass.async_add_executor_job(
                    vikunja_api.create_label, "voice"
                )
                if voice_label:
                    voice_label_id = voice_label.get("id")
        except Exception as label_err:  # noqa: BLE001
            _LOGGER.error("Could not ensure 'voice' label exists: %s", label_err)

    openai_client = OpenAIAPI(openai_api_key)
    users_for_prompt = user_cache_users if enable_user_assignment else []
    openai_response = await hass.async_add_executor_job(
        lambda: openai_client.create_task_from_description(
            task_description,
            projects,
            labels,
            default_due_date,
            voice_correction,
            users=users_for_prompt,
            enable_user_assignment=enable_user_assignment,
        )
    )
    if not openai_response:
        _LOGGER.error("Failed to process task with OpenAI")
        return False, "Sorry, I couldn't process your task due to a connection error. Please try again later.", ""
    try:
        response_data = openai_response if isinstance(openai_response, dict) else json.loads(openai_response)
        task_data = response_data.get("task_data", {})
        if not task_data.get("title"):
            _LOGGER.error("Missing required 'title' field in task data")
            return False, "Sorry, I couldn't understand what task you wanted to create. Please try again.", ""

        extracted_label_ids = []
        if isinstance(task_data, dict) and task_data.get("label_ids"):
            existing_label_ids = {l.get("id") for l in (labels or []) if isinstance(l, dict)}
            for lid in task_data.get("label_ids", []):
                if lid in existing_label_ids:
                    extracted_label_ids.append(lid)
            task_data.pop("label_ids", None)

        assignee_username_or_name = task_data.pop("assignee", None)
        result = await hass.async_add_executor_job(lambda: vikunja_api.add_task(task_data))
        if result:
            try:
                task_id = result.get("id") if isinstance(result, dict) else None
                if task_id:
                    label_ids_to_attach = list(dict.fromkeys(extracted_label_ids))
                    if auto_voice_label and voice_label_id and voice_label_id not in label_ids_to_attach:
                        label_ids_to_attach.append(voice_label_id)
                    for lid in label_ids_to_attach:
                        attach_success = await hass.async_add_executor_job(
                            vikunja_api.add_label_to_task, task_id, lid
                        )
                        if not attach_success:
                            _LOGGER.error("Failed to attach label %s to task %s", lid, task_id)
                    if enable_user_assignment and assignee_username_or_name:
                        # Late import to avoid circulars
                        lookup = assignee_username_or_name.strip().lower()
                        # user_cache_users already prepared list
                        uid = None
                        for u in user_cache_users:
                            uname = str(u.get("username", "")).lower()
                            name = str(u.get("name", "")).lower()
                            if lookup == uname or lookup == name:
                                uid = u.get("id")
                                break
                        if uid is not None:
                            assign_ok = await hass.async_add_executor_job(
                                vikunja_api.assign_user_to_task, task_id, uid
                            )
                            if not assign_ok:
                                _LOGGER.error("Failed to assign user %s to task %s", lookup, task_id)
                        else:
                            _LOGGER.warning("Assignee '%s' not found in cached users", assignee_username_or_name)
            except Exception as attach_err:  # noqa: BLE001
                _LOGGER.error("Error attaching labels/assignee to task: %s", attach_err)

        if result:
            task_title = task_data.get("title")
            _LOGGER.info("Created Vikunja task '%s'", task_title)
            # Build response message
            if not detailed_response:
                return True, f"Successfully added task: {task_title}", task_title

            details_parts = []
            if include_project:
                try:
                    project_id = task_data.get("project_id")
                    if project_id:
                        proj_lookup = {p.get("id"): p.get("title") for p in (projects or []) if isinstance(p, dict)}
                        project_name = proj_lookup.get(project_id, f"Project {project_id}")
                        details_parts.append(f"project '{project_name}'")
                except Exception:  # noqa: BLE001
                    pass
            if include_labels:
                try:
                    label_ids_attached = extracted_label_ids.copy()
                    if auto_voice_label and voice_label_id and voice_label_id in label_ids_attached:
                        # Keep voice label but show at end
                        pass
                    if label_ids_attached:
                        label_lookup = {l.get("id"): l.get("title") for l in (labels or []) if isinstance(l, dict)}
                        label_names = [str(label_lookup.get(lid, str(lid))) for lid in label_ids_attached if lid in label_lookup or lid is not None]
                        if label_names:
                            details_parts.append("labels: " + ", ".join(label_names))
                except Exception:  # noqa: BLE001
                    pass
            if include_due_date:
                due_date = task_data.get("due_date")
                if due_date:
                    details_parts.append(f"due {due_date}")
            if include_assignee and enable_user_assignment:
                assignee_username_or_name = assignee_username_or_name if 'assignee_username_or_name' in locals() else None
                if assignee_username_or_name:
                    details_parts.append(f"assigned to {assignee_username_or_name}")
            detail_suffix = " (" + "; ".join(details_parts) + ")" if details_parts else ""
            return True, f"Successfully added task: {task_title}{detail_suffix}", task_title
        _LOGGER.error("Failed to create task in Vikunja")
        return False, "Sorry, I couldn't add the task to Vikunja. Please check your Vikunja connection.", ""
    except json.JSONDecodeError as err:  # noqa: BLE001
        _LOGGER.error("Failed to parse OpenAI response as JSON: %s", err)
        return False, "Sorry, there was an error processing your task. Please try again.", ""
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Unexpected error creating task: %s", err)
        return False, "Sorry, an unexpected error occurred. Please try again.", ""
