from custom_components.vikunja.helpers.prompt_builder import (
    build_task_creation_messages,
)


def test_prompt_builder_basic():
    msgs = build_task_creation_messages(
        task_description="Buy milk tomorrow",
        projects=[{"id": 1, "title": "General"}],
        labels=[{"id": 5, "title": "groceries"}],
        default_due_date="tomorrow",
        voice_correction=True,
        users=None,
        enable_user_assignment=False,
    )
    assert isinstance(msgs, list) and len(msgs) == 2
    system = msgs[0]["content"]
    assert "Available projects" in system
    assert "DEFAULT DUE DATE RULE" in system
    assert "PRIORITY LEVELS" in system
    assert "RECURRING TASKS" in system


def test_prompt_builder_with_users():
    msgs = build_task_creation_messages(
        task_description="Assign report to Alice",
        projects=[{"id": 1, "title": "General"}],
        labels=[],
        default_due_date="none",
        voice_correction=False,
        users=[{"id": 2, "name": "Alice", "username": "alice"}],
        enable_user_assignment=True,
    )
    system = msgs[0]["content"]
    assert "Available users" in system or "Available users" in system  # tolerant check
    assert "assignee" in system
