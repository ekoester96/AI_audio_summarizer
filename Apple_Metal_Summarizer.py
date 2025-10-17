import sounddevice as sd
import scipy.io.wavfile as wav
from scipy.signal import resample
import subprocess
import requests
import json
import threading
import numpy as np
import os
import sys
import textwrap
import time
import readchar

MODEL_PATH = ""
LLM_MODEL = "gemma3:4b" # example

class LectureRecorder:
    def __init__(self, filename: str = None, model_path: str = MODEL_PATH):
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 44100
        self.target_sample_rate = 16000
        self.recording_thread = None
        self.max_rec_timer = None
        self.filename = filename if filename else "lecture_recording.wav"
        self.model_path = model_path
        whisper_cpp_dir = os.path.dirname(os.path.dirname(model_path))
        self.binary_path = os.path.join(whisper_cpp_dir, "build", "bin", "whisper-cli")
        
    def start_recording(self):
        """Start audio recording with a 90-minute time limit."""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.audio_data = []
        print(" " * 60, end='\r')
        print("\n Recording started... ")
        print(" Max recording time is 90 minutes. Recording will stop automatically if not stopped manually.")
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self._record)
        self.recording_thread.start()

        # Set a timer to stop recording after 90 minutes (5400 seconds)
        MAX_RECORDING_SECONDS = 90 * 60
        self.max_rec_timer = threading.Timer(MAX_RECORDING_SECONDS, self.stop_recording)
        self.max_rec_timer.start()
    
    def _record(self):
        """Record audio in a separate thread"""
        def callback(indata, frames, time, status):
            if status:
                print(f"Status: {status}", file=sys.stderr)
            if self.is_recording:
                self.audio_data.append(indata.copy())
        
        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
            while self.is_recording:
                sd.sleep(100)
    
    def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return
        
        # Check if the timer is alive and cancel it (if stop is manual)
        if self.max_rec_timer and self.max_rec_timer.is_alive():
            self.max_rec_timer.cancel()
            print("\n Recording stopped manually. Processing...")
        else:
            # This means the timer itself triggered the stop
            print("\n Maximum recording time of 90 minutes reached. Stopping automatically.")
            print("\n  Processing...")

        self.is_recording = False
        
        if self.recording_thread:
            self.recording_thread.join()
        
        # Save the audio file
        self.save_audio()
    
    def save_audio(self):
        """Save recorded audio to WAV file"""
        
        audio_array = np.concatenate(self.audio_data, axis=0)
        # Resample to 16000 Hz
        num_samples = int(len(audio_array) * self.target_sample_rate / self.sample_rate)
        audio_resampled = resample(audio_array.flatten(), num_samples)
        # Convert to int16
        audio_int16 = (audio_resampled * 32767).astype(np.int16)
        # Save as 16-bit WAV at 16000 Hz
        wav.write(self.filename, self.target_sample_rate, audio_int16)
        print(f"Audio saved to {self.filename}")
        
        # Transcribe the audio
        self.transcribe_audio()

    def transcribe_audio(self):
    
        print("\n Transcribing audio with whisper.cpp...")

        # --- Path validation (your code is good) ---
        if not os.path.exists(self.binary_path):
            print(f" Binary not found: {self.binary_path}")
            # ... (rest of your error message) ...
            return

        if not os.path.exists(self.model_path):
            print(f" Model not found: {self.model_path}")
            return

        try:
            # Prepare paths
            audio_path = self.filename
            model_path = self.model_path

            # Run whisper.cpp
            cmd = [
                self.binary_path,
                "-f", audio_path,
                "-m", model_path,
                "-l", "en",
                "-t", "8",  # adjust for your cores
                "-nt",      # no timestamps
            ]

            print(f"Running command: {' '.join(cmd)}")
            
            # --- MODIFICATION 1: Capture output for debugging ---
            result = subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True
            )

            # Print whisper's own output/progress, which is useful
            print("\n--- whisper.cpp output ---")

            transcription = result.stdout.strip()

            if '[BLANK_AUDIO]' in transcription:
                print(" No audio detected. The recording was silent or too short.")
                print(" Skipping summarization.")
                # Still delete the audio file since it's blank
                try:
                    os.remove(self.filename)
                    print(f" Blank audio file deleted: {self.filename}")
                except Exception as e:
                    print(f" Could not delete audio file: {e}")
                return

            if not transcription:
                print("No transcription found")

            print("Transcription complete!")
            print(f"\nTranscription Preview:\n{transcription[:200]}...\n")

            # --- MODIFICATION 2: Pass the CORRECT file path for later deletion ---
            self.summarize_with_ollama(transcription)

        except subprocess.CalledProcessError as e:
            print(f"whisper.cpp failed with return code {e.returncode}")
            # Print the error output from whisper.cpp to see what went wrong
            print("\n--- whisper.cpp ERROR output ---")
            print(e.stderr)
            print("--------------------------------")
            
        except Exception as e:
            print(f"An unexpected error occurred during transcription: {e}")

    def summarize_with_ollama(self, transcription):
        """Summarize transcription using Ollama"""
        print("\n Generating summary with Ollama...")
        prompt = f"""
You are an expert lecturer and subject matter analyst. Your task is to review and interpret a lecture transcription.

Follow these steps carefully:

1. Comprehend the lecture content and identify its main ideas.
2. Summarize the lecture clearly and concisely in 3-6 sentences.
3. Extract Key Concepts** — list 3-8 of the most important ideas or principles discussed.
4. Define Important Terms** — identify technical or domain-specific words and provide short, accurate definitions.
5. Generate 5 Quiz Questions** that test understanding of the main topics. Each question should be answerable from the lecture content.

**Lecture Transcription:**
{transcription}

### OUTPUT FORMAT (use exactly this structure):

Summary:
- [Concise summary of the lecture]

Key Concepts:
- [Concept 1]
- [Concept 2]
- [Concept 3]

Terms & Definitions:
- Term: Definition
- Term: Definition

Quiz Questions:
1. [Question 1]
2. [Question 2]
3. [Question 3]
4. [Question 4]
5. [Question 5]

Be confident and professional in tone. Avoid repeating filler phrases or transcribed errors. Focus on clarity and educational value.
"""


        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': LLM_MODEL, # Make sure this model is pulled in Ollama
                    'prompt': prompt,
                    'stream': False
                }
            )
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            summary = response.json()['response']
            
            # Wrap summary text
            lines = summary.split('\n')
            wrapped_lines = [textwrap.fill(line, width=80) for line in lines]
            wrapped_summary = '\n'.join(wrapped_lines)

            print("\n" + "="*80)
            print("LECTURE SUMMARY")
            print("="*80)
            print(wrapped_summary)
            print("="*80)
            
            # Save summary
            summary_file = self.filename.replace('.wav', '_summary.txt')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(wrapped_summary)
            print(f"\n Summary saved to {summary_file}")
            
            # Delete audio file
            try:
                os.remove(self.filename)
                print(f"Audio file deleted: {self.filename}")
            except Exception as e:
                print(f"Could not delete audio file: {e}")
            
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Ollama: {e}")
            print("Make sure Ollama is running ('ollama serve') and the model 'granite3.3:2b' is installed ('ollama pull granite3.3:2b').")
        except Exception as e:
            print(f"An unexpected error occurred during summarization: {e}")


def get_filename():
    # Get filename from user
    filename_input = input("\nEnter filename for audio (without extension): ").strip()
    if not filename_input:
        filename_input = "lecture_recording"
    
    filename = filename_input + ".wav"
    return filename

def main():
    print("LECTURE RECORDER & SUMMARIZER")
    
    filename = get_filename()
    
    recorder = LectureRecorder(filename=filename)
    
    print(f"\n - Audio will be saved as: {filename}")
    print("\n  - Instructions:")
    
    while True:
        if not recorder.is_recording:
             print("Press SPACE to start recording, or 'q' to quit...", end='\r', flush=True)
        
        key = readchar.readkey()
        
        if key.lower() == 'q':
            if recorder.is_recording:
                # Clear the instruction line
                print(" " * 60, end='\r')
                recorder.stop_recording()
                # Wait for all processing to finish before exiting
                time.sleep(1) 
            print("\n Exiting program...")
            break
        elif key == ' ':
            if not recorder.is_recording:
                recorder.start_recording()
            else:
                recorder.stop_recording()

if __name__ == "__main__":
    main()
