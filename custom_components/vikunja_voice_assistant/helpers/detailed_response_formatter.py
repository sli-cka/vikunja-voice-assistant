from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any, Optional

# Optional localization imports are done lazily to avoid circulars when tests import
# this module directly. We keep English defaults if localization module unavailable.
try:  # pragma: no cover - defensive import
    from .localization import (
        build_detailed_parts,
        localized_priority,
        localize_due_phrase,
        localize_repeat_phrase,
        L,
    )
except Exception:  # noqa: BLE001
    build_detailed_parts = None  # type: ignore
    localized_priority = None  # type: ignore


def friendly_due_phrase(iso_dt: str) -> str:
    try:
        cleaned = iso_dt.rstrip("Z")
        # Accept common formats
        dt = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return iso_dt
        today = datetime.now().date()
        ddate = dt.date()
        delta_days = (ddate - today).days
        if delta_days == 0:
            return "today"
        if delta_days == 1:
            return "tomorrow"
        if delta_days < 0:
            return "like currently"
        if 2 <= delta_days < 365:
            return f"in {delta_days} days"
        years = delta_days // 365
        year_word = "year" if years == 1 else "years"
        return f"in {years} {year_word} ({delta_days} days)"
    except Exception:  # noqa: BLE001
        return iso_dt


def friendly_repeat_phrase(repeat_after_seconds: int) -> Optional[str]:
    if not isinstance(repeat_after_seconds, int) or repeat_after_seconds <= 0:
        return None
    if repeat_after_seconds % 86400 != 0:
        return f"repeats every {repeat_after_seconds} seconds"
    days = repeat_after_seconds // 86400
    if 1 <= days < 365:
        phrase = f"repeats in {days} day{'s' if days != 1 else ''}"
    else:
        years = days // 365
        if years >= 1:
            year_word = "year" if years == 1 else "years"
            phrase = f"repeats in {years} {year_word} ({days} days)"
        else:  # fallback
            phrase = f"repeats in {days} days"
    return phrase


def build_detailed_response(
    task_title: str,
    task_data: Dict[str, Any],
    projects: List[Dict[str, Any]] | None,
    labels: List[Dict[str, Any]] | None,
    extracted_label_ids: List[int],
    assignee_username_or_name: Optional[str],
    enable_user_assignment: bool,
    lang: str | None = None,
) -> str:
    """Build a (potentially) localized detailed response string.

    lang: language code; if None or 'en' or localization helpers missing, falls back to English.
    """
    # Collect lookup tables
    project_name: Optional[str] = None
    try:
        project_id = task_data.get("project_id")
        if project_id and project_id != 1:
            proj_lookup: Dict[int, str] = {}
            for p in projects or []:
                if isinstance(p, dict):
                    pid = p.get("id")
                    pname = p.get("title") or p.get("name") or ""
                    if pid is not None and isinstance(pname, str):
                        proj_lookup[pid] = pname.strip()
            raw_name = proj_lookup.get(project_id)
            if raw_name and raw_name.lower() not in {"other", "misc", "general"}:
                project_name = raw_name
    except Exception:  # noqa: BLE001
        project_name = None

    labels_part: Optional[str] = None
    try:
        if extracted_label_ids:
            label_lookup = {
                label_item.get("id"): label_item.get("title")
                for label_item in (labels or [])
                if isinstance(label_item, dict)
            }
            label_names = [
                str(label_lookup.get(lid, str(lid)))
                for lid in extracted_label_ids
                if lid in label_lookup or lid is not None
            ]
            if label_names:
                labels_part = ", ".join(label_names)
    except Exception:  # noqa: BLE001
        labels_part = None

    due_phrase: Optional[str] = None
    due_date = task_data.get("due_date")
    if due_date:
        base_due = friendly_due_phrase(due_date)
        if (
            lang
            and lang != "en"
            and "localize_due_phrase" in globals()
            and "localize_due_phrase"
        ):  # type: ignore
            try:
                due_phrase = localize_due_phrase(base_due, lang)  # type: ignore
            except Exception:  # noqa: BLE001
                due_phrase = base_due
        else:
            due_phrase = base_due

    assignee = (
        assignee_username_or_name
        if enable_user_assignment and assignee_username_or_name
        else None
    )

    priority_word: Optional[str] = None
    try:
        priority = task_data.get("priority")
        if isinstance(priority, int):
            if localized_priority and lang:
                priority_word = localized_priority(priority, lang) or None
            if not priority_word:  # fallback English
                priority_map = {
                    1: "low",
                    2: "medium",
                    3: "high",
                    4: "urgent",
                    5: "do now",
                }
                priority_word = priority_map.get(priority)
    except Exception:  # noqa: BLE001
        priority_word = None

    repeat_phrase: Optional[str] = None
    try:
        repeat_after = task_data.get("repeat_after")
        raw_repeat = (
            friendly_repeat_phrase(repeat_after)
            if isinstance(repeat_after, int)
            else None
        )
        if (
            raw_repeat
            and lang
            and lang != "en"
            and "localize_repeat_phrase" in globals()
        ):  # type: ignore
            try:
                repeat_phrase = localize_repeat_phrase(raw_repeat, lang)  # type: ignore
            except Exception:  # noqa: BLE001
                repeat_phrase = raw_repeat
        else:
            repeat_phrase = raw_repeat
    except Exception:  # noqa: BLE001
        repeat_phrase = None

    # Build parts
    if lang and lang != "en" and build_detailed_parts:
        parts = build_detailed_parts(
            lang=lang,
            project_name=project_name,
            labels_part=labels_part,
            due_phrase=due_phrase,
            assignee=assignee,
            priority_word=priority_word,
            repeat_phrase=repeat_phrase,
        )
        suffix = " (" + "; ".join(parts) + ")" if parts else ""
        if lang and lang != "en" and "L" in globals():  # type: ignore
            try:
                prefix = L("success_added", lang, title=task_title)  # type: ignore
                return f"{prefix}{suffix}"
            except Exception:  # noqa: BLE001
                pass
        return f"Successfully added task: {task_title}{suffix}"

    # English / fallback legacy behavior
    details_parts: List[str] = []
    if project_name:
        details_parts.append(f"project '{project_name}'")
    if labels_part:
        details_parts.append("labels: " + labels_part)
    if due_phrase:
        details_parts.append(f"due {due_phrase}")
    if assignee:
        details_parts.append(f"assigned to {assignee}")
    if priority_word:
        details_parts.append(f"priority {priority_word}")
    if repeat_phrase:
        details_parts.append(repeat_phrase)
    suffix = " (" + "; ".join(details_parts) + ")" if details_parts else ""
    return f"Successfully added task: {task_title}{suffix}"
