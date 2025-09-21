from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any, Optional

def friendly_due_phrase(iso_dt: str) -> str:
    try:
        cleaned = iso_dt.rstrip('Z')
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
        # Future 2..364 days
        if 2 <= delta_days < 365:
            return f"in {delta_days} days"
        # >= 365 days
        years = delta_days // 365
        # Always include total days after number of years
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
        else:  # safety fallback though logically unreachable due to earlier branch
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
) -> str:
    details_parts: List[str] = []
    # Project name (skip generic bucket names)
    try:
        project_id = task_data.get("project_id")
        if project_id and project_id != 1:
            proj_lookup: Dict[int, str] = {}
            for p in (projects or []):
                if not isinstance(p, dict):
                    continue
                pid = p.get("id")
                if pid is None:
                    continue
                pname = p.get("title") or p.get("name") or ""
                if isinstance(pname, str):
                    proj_lookup[pid] = pname.strip()
            project_name = proj_lookup.get(project_id)
            if project_name and project_name.lower() not in {"other", "misc", "general"}:
                details_parts.append(f"project '{project_name}'")
    except Exception:  # noqa: BLE001
        pass

    # Labels (excluding auto voice unless it was originally there; still show if present in extracted list)
    try:
        label_ids_attached = extracted_label_ids.copy()
        if label_ids_attached:
            label_lookup = {l.get("id"): l.get("title") for l in (labels or []) if isinstance(l, dict)}
            label_names = [str(label_lookup.get(lid, str(lid))) for lid in label_ids_attached if lid in label_lookup or lid is not None]
            if label_names:
                details_parts.append("labels: " + ", ".join(label_names))
    except Exception:  # noqa: BLE001
        pass

    # Due date
    due_date = task_data.get("due_date")
    if due_date:
        details_parts.append(f"due {friendly_due_phrase(due_date)}")

    # Assignee
    if enable_user_assignment and assignee_username_or_name:
        details_parts.append(f"assigned to {assignee_username_or_name}")

    # Priority (map 1-5 to words)
    try:
        priority = task_data.get("priority")
        if isinstance(priority, int):
            priority_map = {
                1: "low",
                2: "medium",
                3: "high",
                4: "urgent",
                5: "do now",
            }
            label = priority_map.get(priority)
            if label:
                details_parts.append(f"priority {label}")
    except Exception:  # noqa: BLE001
        pass

    # Repeat
    try:
        repeat_after = task_data.get("repeat_after")
        fr = friendly_repeat_phrase(repeat_after) if isinstance(repeat_after, int) else None
        if fr:
            details_parts.append(fr)
    except Exception:  # noqa: BLE001
        pass

    detail_suffix = " (" + "; ".join(details_parts) + ")" if details_parts else ""
    return f"Successfully added task: {task_title}{detail_suffix}"
