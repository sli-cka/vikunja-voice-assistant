<div align="center">

# 🎙️ Vikunja Voice Assistant for Home Assistant

<img src="https://raw.githubusercontent.com/NeoHuncho/vikunja-voice-assistant/main/logo.png" alt="Vikunja Voice Assistant logo" width="160" />  

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)[![HACS Default](https://img.shields.io/badge/HACS-Default-blue.svg)](https://hacs.xyz/) [![Powered by OpenAI](https://img.shields.io/badge/AI-OpenAI-ff69b4.svg)](https://platform.openai.com/)

Say **“create a task”** or **“add a task”** → Your task goes straight into Vikunja!

*Make creating tasks as easy as talking ✨*
</div>  

---

## ✨ Features

* **Natural voice commands**: *“Create a task…”* or *“Add a task…”* 🗣️
* Supports **project, due date, priority, labels, recurrence** and more 📅
* Optional: speech correction, auto voice label, default due date, user assignment

---

## 📦 Requirements

* [Home Assistant](https://www.home-assistant.io/) with a [voice assistant set up](https://www.home-assistant.io/voice_control/)
* [HACS](https://hacs.xyz/docs/use/download/download/#to-download-hacs-ossupervised)
* Running Vikunja instance + API token
* OpenAI API key

---

## ⚙️ Installation (HACS) | [Full Video Walkthrough](https://github.com/user-attachments/assets/c897b523-2539-42e2-ba03-fa9534a80c36)

⏱️ *Create your first task in under 2 minutes!*

1. In HACS → Search: **Vikunja Voice Assistant** → Install

2. Restart Home Assistant

3. Go to *Settings → Devices & Services → Add Integration*

4. Search: **Vikunja Voice Assistant**

5. Fill out setup form (Vikunja URL, API token, OpenAI key, options)
  <br>
  
   * **Vikunja API Token** → User Settings → API Tokens

     * **Set the following permissions**:
     * Labels: Create, Read All
     * Projects: Read All
     * Tasks: Create
     * Users: Read All (at the bottom of the list) - optional

       📹 [Video Guide](https://github.com/user-attachments/assets/aa60d448-650f-4148-9f11-1e27f12e37ac)

   * **OpenAI API Key** → [Create one here](https://platform.openai.com/account/api-keys)

     📹 [Video Guide](https://github.com/user-attachments/assets/1aae42cb-ba0b-4ebb-951c-bd017da45f71)
<br>
6. ✅ Done – Just say **“create a task”**!

---

## 🔧 Configuration Options

| Option                           | Purpose                                                      | Example/Default |
| -------------------------------- | ------------------------------------------------------------ | --------------- |
| Speech correction                | Fix STT mistakes before parsing                              | On              |
| Auto `voice` label               | Attaches/creates a `voice` label                             | Enabled         |
| Default due date                 | Used if no date & no project given                           | tomorrow        |
| Default due date choices         | none, tomorrow, end\_of\_week, end\_of\_month                | tomorrow        |
| Enable user assignment           | Assign tasks to existing users                               | Disabled        |
| Detailed response (new)          | Speak back richer confirmation details                       | Off             |
| Include project in response      | If detailed response enabled, include project name           | On              |
| Include labels in response       | If detailed response enabled, include label names            | On              |
| Include due date in response     | If detailed response enabled, include ISO due date           | On              |
| Include assignee in response     | If detailed response + assignment, include assignee username | On              |

### Detailed Response Behavior

When disabled (default) the assistant replies with a short confirmation:

`"Successfully added task: Buy milk"`

When enabled, extra context is added based on the toggles you selected, for example:

`"Successfully added task: Buy milk (project 'Groceries'; labels: errands, dairy; due 2025-09-15T12:00:00Z)"`

If user assignment is enabled and detected:

`"Successfully added task: Prepare slides (project 'Work'; due 2025-09-20T17:00:00Z; assigned to william)"`

You can fine‑tune exactly which elements to include without turning off the whole feature.

---

## 🤖 AI Conversation Agent (Recommended)

Append this to your Home Assistant Voice Assistant’s custom instructions:


```
If the user mentions or implies creating or adding a new task, 
always call this tool (do not leave any field empty):

tool_name: VikunjaAddTask
tool_args: {
  task_description: "<exact user sentence>",
}
```
*This will allow your voice assistant to create tasks even if the keywords were missing.*

📹 [Video Guide](https://github.com/user-attachments/assets/0440bc71-b748-4118-8afd-6f0f10b22003)

---

## 🚧 Limitations

* ❌ Only supports **English** commands
* ❌ Cannot create new labels (except auto-creating **voice**)
* ❌ Cannot create new projects
* ❌ Cannot create new assignee users (only assign existing)

---

## 📜 License

MIT – see [LICENSE](LICENSE).
