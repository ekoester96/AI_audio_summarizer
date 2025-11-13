# AI Audio Summarizer 🎙️🤖

Record audio with your device, transcribe it using OpenAI Whisper, and have a local LLM create an intelligent summary of the recording for you. Perfect for customer service calls, lectures, meetings, and more!

## Features

- **Live Audio Recording**: Record audio directly from your device with space bar control
- **Automatic Transcription**: Uses OpenAI Whisper for accurate speech-to-text conversion
- **AI-Powered Summarization**: Leverages Ollama LLMs to generate:
  - Concise lecture summaries
  - Key concepts and main ideas
  - Important terms with definitions
  - Quiz questions to test understanding
- **Cross-Platform**: Separate optimized scripts for macOS/Linux and Windows
- **GPU Acceleration**: macOS M-series chips can use whisper.cpp for faster transcription
- **Auto-Cleanup**: Automatically removes temporary files after processing

## Quick Start

### macOS/Linux Setup
```bash
# Clone the repository
git clone https://github.com/ekoester96/AI_audio_summarizer.git
cd AI_audio_summarizer

# Run the automated setup script
chmod +x setup_mac.sh
./setup_mac.sh
```

### Windows Setup
```powershell
# Clone the repository
git clone https://github.com/ekoester96/AI_audio_summarizer.git
cd AI_audio_summarizer

# Run the automated setup script (as Administrator)
.\setup_windows.ps1
```

## System Requirements

### macOS/Linux
- Python 3.8 or higher
- Homebrew (macOS) or equivalent package manager
- Apple Silicon (M1/M2/M3) recommended for GPU acceleration
- 4GB+ RAM recommended
- Ollama installed and running

### Windows
- Python 3.8 or higher
- Windows 10/11
- 4GB+ RAM recommended
- Ollama installed and running

## Usage

### macOS/Linux
```bash
python3 Apple_audio_summarizer.py
```

### Windows
```bash
python Windows_audio_summarizer.py
```

### Recording Controls

- **SPACE**: Start/Stop recording
- **Q**: Quit the program
- **Maximum Recording Time**: 90 minutes (auto-stops)

### Workflow

1. Run the appropriate script for your OS
2. Enter a filename (or press Enter for default)
3. Press SPACE to start recording
4. Press SPACE again to stop recording
5. Wait for automatic transcription and summarization
6. Find your summary in `[filename]_summary.txt`

## Manual Installation

If you prefer to install dependencies manually:

### macOS/Linux
```bash
# Install Python dependencies
pip install sounddevice scipy numpy openai-whisper requests readchar

# Install whisper.cpp (for GPU acceleration on M-series Macs)
brew install whisper-cpp
bash ./models/download-ggml-model.sh base.en

# Install and setup Ollama
brew install ollama
ollama serve
ollama pull gemma3:4b
```

### Windows
```bash
# Install Python dependencies
pip install sounddevice scipy numpy openai-whisper requests

# Install and setup Ollama
# Download from: https://ollama.com/download
ollama serve
ollama pull granite3.3:2b
```

## Configuration

### Changing the LLM Model

#### macOS (Apple_audio_summarizer.py)
```python
LLM_MODEL = "gemma3:4b"  # Change to your preferred Ollama model
```

#### Windows (Windows_audio_summarizer.py)
```python
OLLAMA_MODEL = 'granite3.3:2b'  # Change to your preferred Ollama model
```

### Changing Whisper Model Path (macOS only)

Update the `MODEL_PATH` variable in `Apple_audio_summarizer.py`:
```python
MODEL_PATH = "/path/to/your/whisper/model/ggml-base.en.bin"
```

### Available Ollama Models
```bash
# List installed models
ollama list

# Pull additional models
ollama pull llama3.2:1b      # Smaller, faster
ollama pull llama3.2:3b      # Balanced
ollama pull granite3.3:2b    # Recommended for Windows
ollama pull gemma3:4b        # Recommended for macOS
```

## 📁 Output Files

After processing, you'll find:
- `[filename]_summary.txt` - AI-generated summary with key concepts, terms, and quiz questions
- Original audio and transcription files are automatically deleted after processing

## Troubleshooting

### "Ollama connection error"
```bash
# Make sure Ollama is running
ollama serve

# Verify the model is installed
ollama list
ollama pull gemma3:4b  # or your chosen model
```

### "Binary not found" (macOS)
```bash
# Reinstall whisper.cpp
brew reinstall whisper-cpp

# Download the model again
cd /opt/homebrew/Cellar/whisper-cpp/[version]/models
bash download-ggml-model.sh base.en
```

### "No module named 'sounddevice'" (Any OS)
```bash
pip install sounddevice scipy numpy openai-whisper requests readchar
```

### Blank Audio Detection (macOS)
If you see `[BLANK_AUDIO]`, ensure:
- Your microphone is properly connected
- System audio permissions are granted
- You're speaking during recording

### Recording Not Starting (Windows)
- Run as Administrator
- Check microphone permissions in Windows Settings
- Ensure no other application is using the microphone

## 🔧 Advanced Configuration

### Adjusting Whisper CPU Threads (macOS)

In `Apple_audio_summarizer.py`, modify the transcription command:
```python
"-t", "8",  # Change to match your CPU core count
```

### Customizing the Summary Prompt

Edit the `prompt` variable in the `summarize_with_ollama()` method to customize the AI's output format and content.

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Submit pull requests
- Improve documentation

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) - Fast C++ implementation
- [Ollama](https://ollama.com/) - Local LLM runtime
- [SoundDevice](https://python-sounddevice.readthedocs.io/) - Audio recording

**Note**: This tool is designed for personal use. Be mindful of privacy and consent when recording conversations with others.

    ollama run granite3.3:2b


    
