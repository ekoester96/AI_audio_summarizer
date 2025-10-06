## AI_audio_summarizer
record and transcribe sound to text with python and have a local LLM create a summary of the recording for you

## 1. Install Python dependencies

    pip install sounddevice scipy numpy openai-whisper requests

# For macOS

## 2. Install system audio backend (if missing)

    brew install portaudio

# 3. Install Ollama

    brew install ollama

# For Windows

    https://ollama.com/download

# 4. Pull the model

    ollama run granite3.3:2b

# 5. Start Ollama service

    ollama serve
