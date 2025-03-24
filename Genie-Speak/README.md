# Genie-Speak

Genie-Speak is a demo application that integrates multi-cloud services to enable seamless voice-based interactions with your data. It includes:

- **Speech-to-Text**: Uses Google Cloud Speech-to-Text API for transcribing audio input.
- **Genie Conversational AI**: Leverages the Databricks Conversational Genie API for intelligent responses to user prompts. The Genie space is set up. And it's using the cookies dataset from Databricks marketplace.
- **Text-to-Speech**: Utilizes ElevenLabs voices (or falls back to pyttsx3) for generating speech output.

## Features

1. Record audio from a microphone and transcribe it using Google Cloud Speech-to-Text.
2. Send transcribed text to the Databricks Genie API for conversational responses.
3. Convert Genie responses to speech using ElevenLabs or pyttsx3.

## Requirements

Install dependencies using the provided `requirements.txt`:

```bash
pip install -r [requirements.txt](http://_vscodecontentref_/0)