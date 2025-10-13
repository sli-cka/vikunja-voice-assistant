import asyncio
import pytest

from custom_components.vikunja_voice_assistant.task_handler import process_task
from custom_components.vikunja_voice_assistant.const import (
    DOMAIN,
    CONF_VIKUNJA_URL,
    CONF_VIKUNJA_API_KEY,
    CONF_OPENAI_API_KEY,
    CONF_DUE_DATE,
    CONF_VOICE_CORRECTION,
    CONF_AUTO_VOICE_LABEL,
    CONF_ENABLE_USER_ASSIGN,
    CONF_DETAILED_RESPONSE,
)
import custom_components.vikunja_voice_assistant.task_handler as th_mod


class FakeHass:
    def __init__(self, domain_config):
        self.data = {DOMAIN: domain_config}

    async def async_add_executor_job(self, func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)


class FakeVikunjaAPI:
    def __init__(self, url, key):  # noqa: D401
        self._projects = []
        self._labels = []
        self._tasks_created = []
        self._assignments = []

    def _set_projects(self, projects):
        self._projects = projects

    def _set_labels(self, labels):
        self._labels = labels

    def get_projects(self):
        return self._projects

    def get_labels(self):
        return self._labels

    def create_label(self, name):
        return {"id": 999, "title": name}

    def add_task(self, task_data):
        task = {"id": 123, **task_data}
        self._tasks_created.append(task)
        return task

    def add_label_to_task(self, task_id, label_id):
        return True

    def assign_user_to_task(self, task_id, user_id):
        self._assignments.append((task_id, user_id))
        return True


class FakeOpenAIAPI:
    def __init__(self, api_key, *_, **__):
        self._next_response = None

    def set_response(self, task_data):
        self._next_response = {"task_data": task_data}

    def create_task_from_description(self, *_, **__):
        return self._next_response


@pytest.fixture(autouse=True)
def patch_apis(monkeypatch):
    fake_vikunja = FakeVikunjaAPI("url", "key")
    fake_openai = FakeOpenAIAPI("key")
    monkeypatch.setattr(th_mod, "VikunjaAPI", lambda *a, **k: fake_vikunja)
    monkeypatch.setattr(th_mod, "OpenAIAPI", lambda *a, **k: fake_openai)
    return fake_vikunja, fake_openai


def base_config(**overrides):
    cfg = {
        CONF_VIKUNJA_URL: "https://example.com/api/v1",
        CONF_VIKUNJA_API_KEY: "vikkey",
        CONF_OPENAI_API_KEY: "openkey",
        CONF_DUE_DATE: "none",
        CONF_VOICE_CORRECTION: True,
        CONF_AUTO_VOICE_LABEL: False,
        CONF_ENABLE_USER_ASSIGN: False,
        CONF_DETAILED_RESPONSE: True,
    }
    normalized = {}
    for k, v in overrides.items():
        if k.startswith("CONF_") and k in globals():
            const_value = globals()[k]
            normalized[const_value] = v
        else:
            normalized[k] = v
    cfg.update(normalized)
    return cfg


def test_process_task_minimal(patch_apis):
    fake_vikunja, fake_openai = patch_apis
    fake_vikunja._set_projects([])
    fake_vikunja._set_labels([])
    fake_openai.set_response({"title": "Buy milk", "project_id": 1})
    hass = FakeHass(base_config(CONF_DETAILED_RESPONSE=False))
    ok, msg, title = asyncio.run(process_task(hass, "Buy milk", []))
    assert ok is True
    assert title == "Buy milk"
    assert msg == "Successfully added task: Buy milk"


def test_process_task_detailed_with_metadata(patch_apis):
    fake_vikunja, fake_openai = patch_apis
    fake_vikunja._set_projects([{"id": 2, "title": "Home"}])
    fake_vikunja._set_labels([{"id": 9, "title": "errand"}])
    fake_openai.set_response(
        {
            "title": "Buy milk",
            "project_id": 2,
            "due_date": "2099-01-01",
            "priority": 3,
            "repeat_after": 86400,
            "label_ids": [9],
        }
    )
    hass = FakeHass(base_config())
    ok, msg, title = asyncio.run(process_task(hass, "Buy milk for home", []))
    assert ok is True
    assert title == "Buy milk"
    assert "project 'Home'" in msg
    assert "labels:" in msg
    assert "due" in msg
    assert "priority" in msg
    assert "repeats" in msg


def test_process_task_with_assignee(patch_apis):
    fake_vikunja, fake_openai = patch_apis
    fake_vikunja._set_projects([])
    fake_vikunja._set_labels([])
    fake_openai.set_response(
        {"title": "Prepare slides", "project_id": 1, "assignee": "alice"}
    )
    users = [{"id": 7, "username": "alice", "name": "Alice"}]
    hass = FakeHass(base_config(CONF_ENABLE_USER_ASSIGN=True))
    ok, msg, title = asyncio.run(
        process_task(hass, "prepare slides assign to alice", users)
    )
    assert ok is True
    assert "assigned to alice" in msg
    assert fake_vikunja._assignments == [(123, 7)]


def test_process_task_openai_failure(patch_apis, monkeypatch):
    fake_vikunja, fake_openai = patch_apis
    # Force OpenAI to return None
    fake_openai.set_response(None)
    hass = FakeHass(base_config())
    ok, msg, title = asyncio.run(process_task(hass, "some description", []))
    assert ok is False
    assert "couldn't process" in msg.lower()
    assert title == ""


def test_process_task_missing_title(patch_apis):
    fake_vikunja, fake_openai = patch_apis
    # Provide response missing title
    fake_openai.set_response({"task_data": {"project_id": 1}})  # malformed
    hass = FakeHass(base_config())
    ok, msg, title = asyncio.run(process_task(hass, "whatever", []))
    assert ok is False
    assert "couldn't understand" in msg.lower()
    assert title == ""
