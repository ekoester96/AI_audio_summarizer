## AI_audio_summarizer
Record audio with your device then transcribe the audio file using openai whisper and have a local LLM summarize the audio transcript for you. Could be great for customer service calls, lectures, or meetings. For apple M series chips you can use whisper.cpp to enable the gpu for transcribing which is much faster than the cpu but it might be more difficult when installing dependencies. 

# Python dependencies

    pip install sounddevice scipy numpy openai-whisper requests readchar

## For macOS make a directory to hold whisper.cpp models in a user directory

    brew install whisper-cpp

# if the model ggml-base.en.bin is not in the models directory then run this command:

    bash ./models/download-ggml-model.sh base.en

# macOS Install Ollama

    brew install ollama

# Pull a model

    ollama run granite3.3:2b

## For Windows download Ollama and use the non Apple version of the script

    https://ollama.com/download

    ollama run granite3.3:2b


    
