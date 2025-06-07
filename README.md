# Vikunja Todo AI for Home Assistant

This integration allows you to create tasks in your Vikunja instance using voice commands via Home Assistant. It utilizes OpenAI to parse natural language and extract relevant information like project, date, and time.

## Features
- Trigger task creation by voice using the keyword "todo"
- Automatically detect mentioned projects and assign tasks accordingly
- Extract date and time information for task scheduling
- Falls back to default project (ID: 1) when no project is specified
- Choose between GPT-4.1-mini (default, more economical) or GPT-4.1 models

## Requirements
- Home Assistant 
- A running Vikunja instance
- OpenAI API key
- HACS (Home Assistant Community Store)

## Installation
1. Add this repository to HACS as a custom repository
2. Install the "Vikunja Todo AI" integration from HACS
3. Configure the integration with your Vikunja server details

## Configuration

Add the following to your `configuration.yaml`:

```yaml
vikunja_todo_ai:
  url: https://your-vikunja-instance.com
  api_token: your-vikunja-api-token
  openai_api_key: your-openai-api-key
  openai_model: gpt-4.1-mini  # Optional, defaults to gpt-4.1-mini, can be gpt-4.1
```

## Usage
Simply say "todo" followed by your task description to your voice assistant.
Examples:
- "Todo: Buy milk tomorrow"
- "Todo: Finish report for work project by Friday"
- "Todo: Call mom at 3 PM"

## Support
If you have any issues or feature requests, please create an issue in the GitHub repository.