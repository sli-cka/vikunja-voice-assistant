<div align="center">

# Vikunja Voice Assistant for Home Assistant

Create structured Vikunja tasks hands‑free via Home Assistant's conversation agent (Assist) using OpenAI for natural language parsing.

</div>

## ✨ What It Does
Turn phrases like:
> "Add task finish quarterly finance report for work next Friday at 5pm high priority"

into a properly formed Vikunja task with project, due date, priority, labels (optional auto 'voice' label) and recurrence when spoken.

## 🚀 Key Features
* Voice or text conversation task creation (Assist intent)
* Project + label detection (uses existing IDs, no guessing new labels except optional auto 'voice')
* Optional automatic speech-to-text correction mode
* Configurable default due date strategy (none / tomorrow / end of week / end of month)
* Optional automatic 'voice' label creation + attachment
* Lightweight logging (errors + successes only)

## 📦 Requirements
* Home Assistant (2024.x+ recommended)
* Running Vikunja instance + API token (user settings -> API tokens)
* OpenAI API key
* HACS (for easy installation/updates)

---
## 🛠 Installation (HACS)
Right after cloning or for end users:
1. In Home Assistant go to HACS → Integrations → 3‑dot menu → Custom repositories
2. Add this repo URL and choose category: Integration
3. Search HACS for "Vikunja Voice Assistant" and install
4. Restart Home Assistant if prompted
5. Go to Settings → Devices & Services → Add Integration → search "Vikunja Voice Assistant"
6. Enter:
	 * Vikunja base URL (root, the integration will append /api/v1 if needed)
	 * Vikunja API Token
	 * OpenAI API Key
	 * Toggle options (speech correction, auto 'voice' label)
	 * Default due date preference

That's it—the intent sentences are auto‑installed and Assist is reloaded.

## ⚙️ Configuration Options
| Option | Description |
|--------|-------------|
| Speech correction | Improves parsing by correcting typical STT misspellings |
| Auto 'voice' label | Ensures/creates a label named `voice` and attaches it |
| Default due date | Applied only when user gives no project + no date |
| Default due date choices | none, tomorrow, end_of_week, end_of_month |

## 🗣 Usage Examples
Speak (or type into conversation):
* "Add task buy milk with grocery label tomorrow"
* "Add task schedule dentist appointment next March"
* "Add task take vitamins daily"
* "Add task finish marketing plan by Friday 5pm high priority"

Response will confirm creation, e.g. "Successfully added task: Finish marketing plan".

## 🔐 Privacy / Network
* Sends only the task phrase plus available project + label names to OpenAI for structured extraction.
* No task history or unrelated Home Assistant data is transmitted.

## 🧪 Troubleshooting
| Issue | Check |
|-------|-------|
| Cannot connect | URL must be reachable from HA, include https and not duplicate /api/v1 path |
| Invalid OpenAI key | Confirm key not expired; no leading/trailing spaces |
| Tasks missing labels | Ensure label already exists in Vikunja (except auto 'voice') |
| Wrong due date | Confirm timezone of HA host and phrase specificity |

Enable debug locally (not default) by adding to `configuration.yaml`:
```
logger:
	logs:
		custom_components.vikunja_voice_assistant: debug
```

## 🤝 Contributing
Small focused PRs welcome. Before submitting:
1. Keep logging minimal (debug only when truly needed)
2. Follow existing naming style (snake_case, concise)
3. Add/update doc snippets if behavior changes
4. Include a short screen recording or screenshot for UI / flow changes

See `.github/CONTRIBUTING.md` for details.

## 🐞 Reporting Issues
Open an issue and include:
* Clear title
* Reproduction steps
* Expected vs actual
* Screenshot or short video (required)
* Redacted logs (if relevant)

## 📄 License
MIT – see `LICENSE`.

## 🙏 Acknowledgements
* Vikunja project team
* Home Assistant community

---
Enjoy faster inbox‑zero for your tasks ✨