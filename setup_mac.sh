#!/bin/bash

echo "======================================"
echo "AI Audio Summarizer - macOS Setup"
echo "======================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Error: Homebrew is not installed.${NC}"
    echo "Please install Homebrew first:"
    echo '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
fi

echo -e "${GREEN}✓ Homebrew found${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo "Installing Python 3 via Homebrew..."
    brew install python3
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install sounddevice scipy numpy openai-whisper requests readchar

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install Python dependencies${NC}"
    exit 1
fi

# Install whisper.cpp
echo ""
echo "Installing whisper.cpp..."
if ! command -v whisper-cli &> /dev/null; then
    brew install whisper-cpp
    echo -e "${GREEN}✓ whisper.cpp installed${NC}"
else
    echo -e "${YELLOW}! whisper.cpp already installed${NC}"
fi

# Download Whisper model
echo ""
echo "Downloading Whisper base.en model..."
WHISPER_PATH=$(brew --prefix whisper-cpp)
MODEL_DIR="$WHISPER_PATH/models"

if [ ! -d "$MODEL_DIR" ]; then
    mkdir -p "$MODEL_DIR"
fi

cd "$MODEL_DIR" || exit

if [ ! -f "ggml-base.en.bin" ]; then
    # Download the model download script if it doesn't exist
    if [ ! -f "download-ggml-model.sh" ]; then
        curl -O https://raw.githubusercontent.com/ggerganov/whisper.cpp/master/models/download-ggml-model.sh
        chmod +x download-ggml-model.sh
    fi
    bash download-ggml-model.sh base.en
    echo -e "${GREEN}✓ Whisper model downloaded${NC}"
else
    echo -e "${YELLOW}! Whisper model already exists${NC}"
fi

# Update MODEL_PATH in the Python script
cd - || exit
MODEL_PATH="$MODEL_DIR/ggml-base.en.bin"

if [ -f "Apple_audio_summarizer.py" ]; then
    # Check if MODEL_PATH is already set
    if grep -q 'MODEL_PATH = ""' Apple_audio_summarizer.py; then
        # macOS compatible sed
        sed -i '' "s|MODEL_PATH = \"\"|MODEL_PATH = \"$MODEL_PATH\"|g" Apple_audio_summarizer.py
        echo -e "${GREEN}✓ Updated MODEL_PATH in Apple_audio_summarizer.py${NC}"
    else
        echo -e "${YELLOW}! MODEL_PATH already configured in Apple_audio_summarizer.py${NC}"
    fi
fi

# Install Ollama
echo ""
echo "Checking for Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    brew install ollama
    echo -e "${GREEN}✓ Ollama installed${NC}"
else
    echo -e "${YELLOW}! Ollama already installed${NC}"
fi

# Start Ollama service
echo ""
echo "Starting Ollama service..."
brew services start ollama
sleep 3

# Pull the default model
echo ""
echo "Pulling gemma3:4b model (this may take a few minutes)..."
ollama pull gemma3:4b

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ gemma3:4b model ready${NC}"
else
    echo -e "${RED}✗ Failed to pull model. You can do this manually later with: ollama pull gemma3:4b${NC}"
fi

# Final message
echo ""
echo "======================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================"
echo ""
echo "To run the audio summarizer:"
echo "  python3 Apple_audio_summarizer.py"
echo ""
echo "Make sure Ollama is running:"
echo "  ollama serve"
echo ""
echo "Optional: Pull additional models:"
echo "  ollama pull llama3.2:1b"
echo "  ollama pull llama3.2:3b"
echo ""
