import sys
from pathlib import Path
import types

# Provide lightweight Home Assistant stubs ONLY if the real package is absent.
# This lets the integration's __init__ import succeed in CI without adding
# test-specific logic to production code.
if "homeassistant" not in sys.modules:  # pragma: no cover
    ha_mod = types.ModuleType("homeassistant")
    helpers_mod = types.ModuleType("homeassistant.helpers")
    intent_mod = types.ModuleType("homeassistant.helpers.intent")
    core_mod = types.ModuleType("homeassistant.core")
    config_entries_mod = types.ModuleType("homeassistant.config_entries")

    class HomeAssistant:  # minimal subset used in tests
        def __init__(self):
            self.data = {}

            class _Cfg:
                config_dir = "."

            self.config = _Cfg()

            class _Services:
                async def async_call(self, *a, **k):  # noqa: D401
                    return True

                def async_register(self, *a, **k):  # noqa: D401
                    return True

            self.services = _Services()

        def async_create_task(self, *_, **__):
            return None

    class ConfigEntry:  # placeholder
        def __init__(self, data=None):
            self.data = data or {}

    class ServiceCall:  # placeholder for type reference
        def __init__(self, data=None):
            self.data = data or {}

    class _CV:  # stub for config_validation
        @staticmethod
        def config_entry_only_config_schema(_domain):  # noqa: D401
            return {}

    class _CVNamespace:
        @staticmethod
        def config_entry_only_config_schema(_domain):  # noqa: D401
            return {}

        @staticmethod
        def string(value):  # simplistic passthrough validator
            return str(value)

        @staticmethod
        def positive_int(value):
            iv = int(value)
            if iv <= 0:
                raise ValueError("expected positive int")
            return iv

    # Populate helper validation namespace dynamically to satisfy runtime without static attr assignment
    helpers_mod.__dict__["config_validation"] = _CVNamespace  # dynamic injection

    class _Intent:  # minimal placeholder
        def __init__(self, language="en", slots=None):
            self.language = language
            self.slots = slots or {}

    class _IntentResponse:
        def __init__(self, language="en"):
            self.language = language
            self._speech = None

        def async_set_speech(self, text):  # noqa: D401
            self._speech = text

    class _IntentHandler:
        intent_type = "StubIntent"

        async def async_handle(self, call):  # noqa: D401
            return _IntentResponse(call.language)

    def async_register(_hass, _handler):  # noqa: D401
        return True

    # Update intent and core modules via __dict__ to avoid Pylance attr warnings
    intent_mod.__dict__.update(
        {
            "Intent": _Intent,
            "IntentResponse": _IntentResponse,
            "IntentHandler": _IntentHandler,
            "async_register": async_register,
        }
    )
    core_mod.__dict__.update(
        {
            "HomeAssistant": HomeAssistant,
            "ServiceCall": ServiceCall,
        }
    )
    config_entries_mod.__dict__.update(
        {
            "ConfigEntry": ConfigEntry,
        }
    )

    # Register modules in sys.modules hierarchy
    sys.modules["homeassistant"] = ha_mod
    sys.modules["homeassistant.helpers"] = helpers_mod
    sys.modules["homeassistant.core"] = core_mod
    sys.modules["homeassistant.config_entries"] = config_entries_mod
    sys.modules["homeassistant.helpers.intent"] = intent_mod

# Ensure project root is on sys.path so 'custom_components' is importable when
# running tests directly (outside Home Assistant environment).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
