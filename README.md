<div align="center">

# Vikunja Voice Assistant for Home Assistant

<img src="https://raw.githubusercontent.com/NeoHuncho/vikunja-voice-assistant/main/logo.png" alt="Vikunja Voice Assistant logo" width="160" />

Create structured Vikunja tasks hands‑free via Home Assistant's voice assistant using AI for natural language parsing.

</div>

## ✨ How to Use
Tell your Home Assistant voice assistant to **create** or **add** a task, then speak the details. You can include:
- Project
- Due date and time
- Priority
- Labels
- Recurrence

Example:
> "Add task pump bike tires every month starting tomorrow with the label maintenance. Oh yeah and make it high priority."

---
## 🛠 Installation (HACS)

### 📦 Requirements
* Home Assistant
* Running Vikunja instance + API token (user settings -> API tokens)
* OpenAI API key
* HACS

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
| Enable user assignment (new) | When enabled, the integration periodically fetches all users (A-Z search) and allows specifying an assignee in a natural phrase (e.g. "assign to William"). |

### 👥 User Assignment (Optional Feature)
Disabled by default. When you enable it in the configuration:
1. The integration builds a local cache (`vikunja_users.json`) in your HA config directory by querying Vikunja users A–Z.
2. It refreshes every 24 hours automatically.
3. You can say things like:
	* "Add task prepare slides for next week assign to William"
	* "Create task review PR for bob tomorrow"

If the assistant clearly identifies a user, it adds an `assignee` field and the integration assigns the task after creation.

Service to force refresh the user cache:
`vikunja.refresh_user_cache`

If a referenced user isn't found in the cache, the task is still created without an assignee.

## 🗣 Usage Examples
Speak (or type into conversation):
* "Add task buy milk with grocery label tomorrow"
* "Add task schedule dentist appointment next March"
* "Add task take vitamins daily"
* "Add task finish the planting tomatoes to the project garden with high priority. Make it due next Friday."

Response will confirm creation, e.g. "Successfully added task: Finish the planting tomatoes "

## 📄 License
MIT – see `LICENSE`.
