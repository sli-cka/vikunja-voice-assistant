from custom_components.vikunja_voice_assistant.helpers.detailed_response_formatter import (
    friendly_repeat_phrase,
    build_detailed_response,
)


def test_friendly_repeat_phrase_basic():
    assert friendly_repeat_phrase(86400) == "repeats in 1 day"
    assert friendly_repeat_phrase(86400 * 3) == "repeats in 3 days"


def test_friendly_repeat_phrase_years():
    one_year = 365 * 86400
    fr = friendly_repeat_phrase(one_year)
    assert fr is not None and "1 year" in fr


def test_build_detailed_response_minimal():
    msg = build_detailed_response(
        task_title="Buy milk",
        task_data={"title": "Buy milk", "project_id": 1},
        projects=[],
        labels=[],
        extracted_label_ids=[],
        assignee_username_or_name=None,
        enable_user_assignment=False,
    )
    assert msg.startswith("Successfully added task: Buy milk")


def test_build_detailed_response_full():
    projects = [{"id": 2, "title": "Home"}]
    labels = [{"id": 10, "title": "errand"}]
    msg = build_detailed_response(
        task_title="Buy milk",
        task_data={
            "title": "Buy milk",
            "project_id": 2,
            "due_date": "2099-12-01",
            "priority": 3,
            "repeat_after": 86400,
        },
        projects=projects,
        labels=labels,
        extracted_label_ids=[10],
        assignee_username_or_name="alice",
        enable_user_assignment=True,
    )
    assert "project" in msg
    assert "labels:" in msg
    assert "due" in msg
    assert "priority" in msg
    assert "repeats" in msg
    assert "assigned to alice" in msg
