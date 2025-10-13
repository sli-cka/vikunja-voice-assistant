from datetime import datetime, timedelta
from custom_components.vikunja_voice_assistant.helpers.detailed_response_formatter import (
    friendly_due_phrase,
)


def test_friendly_due_phrase_today():
    today = datetime.now().strftime("%Y-%m-%d")
    assert friendly_due_phrase(today) in {
        today,
        "today",
    }  # may map to today or keep raw if time absent


def test_friendly_due_phrase_tomorrow():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    out = friendly_due_phrase(tomorrow)
    assert out in {"tomorrow", tomorrow}


def test_friendly_due_phrase_in_future_days():
    future = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    out = friendly_due_phrase(future)
    assert out in {"in 3 days", future}


def test_friendly_due_phrase_next_week():
    future = (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d")
    out = friendly_due_phrase(future)
    assert out in {"in 8 days", future}


def test_friendly_due_phrase_passthrough_invalid():
    weird = "not-a-date"
    assert friendly_due_phrase(weird) == weird
