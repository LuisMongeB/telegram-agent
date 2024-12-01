# Telegram AI Agent

A Telegram bot that leverages OpenAI's capabilities to transcribe voice messages and provide intelligent summaries. The bot listens for voice messages, once a voice message is received, it starts the LangGraph agent workflow to process them using OpenAI's speech-to-text API, and returns concise summaries back to the chat.

> **Current Status**: Version 0.1 - Local polling implementation  
> **Coming Soon**: Webhook implementation with Azure Functions

## Features

- Voice message transcription
- AI-powered message summarization
- Real-time processing
- Error handling and logging

## Prerequisites

- Python 3.11
- Telegram Bot Token
- OpenAI API Key

## Installation

```pip install -r requirements.txt``` on the root directory.

## Configuration

## Usage

## Project Structure

```
.
├── README.md
├── requirements.txt
├── src
│   ├── __init__.py
│   ├── agents
│   │   ├── __init__.py
│   │   ├── audio_buffer.py
│   │   ├── audio_processor.py
│   │   ├── message_handler.py
│   │   ├── responder.py
│   │   └── summarizer.py
│   ├── config.py
│   ├── downloads
│   │   ├── temp
│   │   └── example.mp3
│   ├── main.py
│   └── telegram_utils
│       ├── __init__.py
│       └── telegram_helpers.py
└── tests
    ├── __init__.py
    └── test_agents
        └── __init__.py
```

## Contributing

## License