# Vikunja voice assistant for Home Assistant

This integration allows you to create tasks in your Vikunja instance using voice commands via Home Assistant. It utilizes OpenAI to parse natural language and extract relevant information like project, date, and time.

## Features
- Trigger task creation by voice using the keyword "add" and "task"
- Automatically detect mentioned projects and assign tasks accordingly
- Extract date and time information for task scheduling
- Choose between GPT-4.1-mini (default, more economical) or GPT-4.1 models

## Requirements
- Home Assistant 
- A running Vikunja instance and a generated API key
- OpenAI API key
- HACS (Home Assistant Community Store)

## Installation
1. Add this repository to HACS as a custom repository
2. Install the "Vikunja voice assistant" integration from HACS
3. Configure the integration with your Vikunja server details

## Configuration

## Usage
Simply say "add task" followed by your task description. Examples:
- "Add task to project Home Renovation to paint the living room tomorrow at 3 PM"
- "Add task to Work project to submit the report by next Friday"

## Support
If you have any issues or feature requests, please create an issue in the GitHub repository.