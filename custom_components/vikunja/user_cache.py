from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .const import (
    USER_CACHE_FILENAME,
    USER_CACHE_REFRESH_HOURS,
    CONF_ENABLE_USER_ASSIGN,
    CONF_VIKUNJA_URL,
    CONF_VIKUNJA_API_KEY,
    DOMAIN,
)
from .api.vikunja_api import VikunjaAPI

_LOGGER = logging.getLogger(__name__)

VOWEL_SEARCH_SET = ["a", "e", "i", "o", "u", "y"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_initial_user_cache_sync(hass_config_dir: str, vikunja_url: str, api_key: str) -> None:
    """Initial synchronous (executor) build for config flow usage.

    Performs vowel searches once and writes the cache file. Errors are swallowed
    (reported via logging) so that the config flow can proceed.
    """
    try:
        api = VikunjaAPI(vikunja_url, api_key)
        combined: Dict[str, Dict[str, Any]] = {}
        for letter in VOWEL_SEARCH_SET:
            try:
                users = api.search_users(letter) or []
                for u in users:
                    if isinstance(u, dict) and u.get("id") is not None:
                        key = str(u.get("id"))
                        if key not in combined:
                            combined[key] = {
                                "id": u.get("id"),
                                "name": u.get("name"),
                                "username": u.get("username"),
                            }
            except Exception:  # noqa: BLE001
                continue
        path = os.path.join(hass_config_dir, USER_CACHE_FILENAME)
        data = {"users": list(combined.values()), "last_refresh": _utc_now_iso()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Initial user cache build failed (non-fatal): %s", err)


@dataclass
class UserCache:
    users: List[Dict[str, Any]] = field(default_factory=list)
    last_refresh: Optional[str] = None

    @property
    def age_hours(self) -> Optional[float]:
        if not self.last_refresh:
            return None
        try:
            last = datetime.fromisoformat(self.last_refresh.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - last).total_seconds() / 3600
        except Exception:  # noqa: BLE001
            return None


class VikunjaUserCacheManager:
    """Manages persistent user cache lifecycle."""

    def __init__(self, hass):
        from homeassistant.core import HomeAssistant  # local import for typing

        self.hass: "HomeAssistant" = hass
        self.cache_path = os.path.join(hass.config.config_dir, USER_CACHE_FILENAME)
        self.data = UserCache()

    # --------------- Persistence helpers ---------------
    def _load_sync(self) -> UserCache:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict) and isinstance(raw.get("users"), list):
                    return UserCache(users=raw.get("users", []), last_refresh=raw.get("last_refresh"))
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Failed loading user cache: %s", err)
        return UserCache()

    def _save_sync(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({"users": self.data.users, "last_refresh": self.data.last_refresh}, f, indent=2)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed saving user cache: %s", err)

    async def load(self) -> None:
        self.data = await self.hass.async_add_executor_job(self._load_sync)

    # --------------- Refresh logic ---------------
    def _refresh_sync(self, vikunja_url: str, api_key: str) -> UserCache:
        api = VikunjaAPI(vikunja_url, api_key)
        combined: Dict[str, Dict[str, Any]] = {}
        for letter in VOWEL_SEARCH_SET:
            try:
                for u in api.search_users(letter) or []:
                    if isinstance(u, dict) and u.get("id") is not None:
                        key = str(u.get("id"))
                        if key not in combined:
                            combined[key] = {
                                "id": u.get("id"),
                                "name": u.get("name"),
                                "username": u.get("username"),
                            }
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("User search failed for '%s': %s", letter, err)
        new_cache = UserCache(users=list(combined.values()), last_refresh=_utc_now_iso())
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({"users": new_cache.users, "last_refresh": new_cache.last_refresh}, f, indent=2)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed writing user cache: %s", err)
        return new_cache

    async def refresh(self, force: bool = False) -> None:
        domain_config = self.hass.data.get(DOMAIN, {})
        if not domain_config.get(CONF_ENABLE_USER_ASSIGN):
            return
        vikunja_url = domain_config.get(CONF_VIKUNJA_URL)
        api_key = domain_config.get(CONF_VIKUNJA_API_KEY)
        if not (vikunja_url and api_key):
            return
        if not force and self.data.age_hours is not None and self.data.age_hours < USER_CACHE_REFRESH_HOURS:
            return
        self.data = await self.hass.async_add_executor_job(self._refresh_sync, vikunja_url, api_key)
        _LOGGER.info("Vikunja user cache refreshed: %s users", len(self.data.users))

    # --------------- Scheduling ---------------
    def schedule_periodic_refresh(self) -> None:
        """Schedule periodic refresh task via HA helper."""
        try:
            from homeassistant.helpers.event import async_track_time_interval
            interval = timedelta(hours=USER_CACHE_REFRESH_HOURS)

            async def _scheduled(_now):  # noqa: D401
                await self.refresh()

            async_track_time_interval(self.hass, _scheduled, interval)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to schedule user cache refresh: %s", err)

    # --------------- Lookup helper ---------------
    def find_user_id(self, lookup: str) -> Optional[int]:
        lookup_l = lookup.strip().lower()
        for u in self.data.users:
            try:
                if lookup_l in {str(u.get("username", "")).lower(), str(u.get("name", "")).lower()}:
                    return u.get("id")
            except Exception:  # noqa: BLE001
                continue
        return None
