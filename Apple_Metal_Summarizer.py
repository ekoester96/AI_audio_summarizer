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

try:
    # Windows
    import msvcrt
    def getch():
        """Gets a single character from the user without waiting for enter."""
        return msvcrt.getch().decode()
except ImportError:
    # Unix-like (Linux, macOS)
    import tty, termios
    def getch():
        """Gets a single character from the user without waiting for enter."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class LectureRecorder:
    def __init__(self, filename: str = None, model_path: str = "/Users/ethankoester-schmidt/developer/whisper.cpp/models/ggml-base.en.bin"):
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
        if not self.audio_data:
            print("No audio data recorded!")
            return
        
        audio_array = np.concatenate(self.audio_data, axis=0)
        # Resample to 16000 Hz
        num_samples = int(len(audio_array) * self.target_sample_rate / self.sample_rate)
        audio_resampled = resample(audio_array.flatten(), num_samples)
        # Convert to int16
        audio_int16 = (audio_resampled * 32767).astype(np.int16)
        # Save as 16-bit WAV at 16000 Hz
        wav.write(self.filename, self.target_sample_rate, audio_int16)
        print(f"✅ Audio saved to {self.filename}")
        
        # Transcribe the audio
        self.transcribe_audio()

    def transcribe_audio(self):
    
        print("\n🎙️ Transcribing audio with whisper.cpp...")

        # --- Path validation (your code is good) ---
        if not os.path.exists(self.binary_path):
            print(f"❌ Binary not found: {self.binary_path}")
            # ... (rest of your error message) ...
            return

        if not os.path.exists(self.model_path):
            print(f"❌ Model not found: {self.model_path}")
            return

        try:
            # Prepare paths
            audio_path = self.filename
            model_path = self.model_path
            # This is the correct path whisper.cpp will create with the -otxt flag
            transcription_file_path = audio_path + ".txt"

            # Run whisper.cpp
            cmd = [
                self.binary_path,
                "-f", audio_path,
                "-m", model_path,
                "-l", "en",
                "-t", "8",  # adjust for your cores
                "-nt",      # no timestamps
                "-otxt"     # output to .txt file
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
            print(result.stderr) # whisper.cpp often prints progress to stderr
            print("--------------------------")

            transcription = ""
            if os.path.exists(transcription_file_path):
                with open(transcription_file_path, 'r', encoding='utf-8') as f:
                    transcription = f.read().strip()
            else:
                # This will now be a more meaningful error
                print(f"❌ Transcription file not found after running whisper.cpp: {transcription_file_path}")
                print("This can happen if the audio was silent or too short.")
                return

            # Check if transcription is empty
            if not transcription:
                print("⚠️  Transcription is empty. The audio might have been silent. Aborting summarization.")
                return

            print("✅ Transcription complete!")
            print(f"\nTranscription Preview:\n{transcription[:200]}...\n")

            # --- MODIFICATION 2: Pass the CORRECT file path for later deletion ---
            self.summarize_with_ollama(transcription, transcription_file_path)

        except subprocess.CalledProcessError as e:
            print(f"❌ whisper.cpp failed with return code {e.returncode}")
            # Print the error output from whisper.cpp to see what went wrong
            print("\n--- whisper.cpp ERROR output ---")
            print(e.stderr)
            print("--------------------------------")
            
        except Exception as e:
            print(f"❌ An unexpected error occurred during transcription: {e}")

    def summarize_with_ollama(self, transcription, transcription_file_to_delete):
        """Summarize transcription using Ollama"""
        print("\n Generating summary with Ollama...")
        
        prompt = f"""You are an expert in your field be confident in your answers. Please analyze this lecture transcription and provide:

    1. A concise summary of the main topics covered
    2. Key concepts discussed
    3. Important terms and their definitions
    4. Generate 5 quiz questions based on the lecture transcription

    Lecture Transcription:
    {transcription}

    Please format your response clearly with sections for Summary, Key Concepts, and Terms & Definitions, and 5 questions from the summary that could be on a quiz."""

        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'granite3.3:2b', # Make sure this model is pulled in Ollama
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
            print(f"\n✅ Summary saved to {summary_file}")
            
            # --- MODIFICATION 3: Use the correct filename variable passed from the previous function ---
            try:
                os.remove(transcription_file_to_delete)
                print(f"🗑️  Transcription file deleted: {transcription_file_to_delete}")
            except Exception as e:
                print(f"⚠️  Could not delete transcription file: {e}")
            
            # Delete audio file
            try:
                os.remove(self.filename)
                print(f"🗑️  Audio file deleted: {self.filename}")
            except Exception as e:
                print(f"⚠️  Could not delete audio file: {e}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error connecting to Ollama: {e}")
            print("Make sure Ollama is running ('ollama serve') and the model 'granite3.3:2b' is installed ('ollama pull granite3.3:2b').")
        except Exception as e:
            print(f"❌ An unexpected error occurred during summarization: {e}")


def main():
    print("="*60)
    print("LECTURE RECORDER & SUMMARIZER")
    print("="*60)
    
    # Get filename from user
    filename_input = input("\nEnter filename for audio (without extension): ").strip()
    if not filename_input:
        filename_input = "lecture_recording"
    
    filename = filename_input + ".wav"
    
    recorder = LectureRecorder(filename=filename)
    
    print(f"\nAudio will be saved as: {filename}")
    print("\n  Instructions:")
    print("  - Press SPACE to start/stop recording")
    print("  - Press 'q' to exit\n")
    
    # Main input loop
    while True:
        if not recorder.is_recording:
             print("Press SPACE to start recording, or 'q' to quit...", end='\r', flush=True)
        
        char = getch() 
        
        if char.lower() == 'q':
            if recorder.is_recording:
                # Clear the instruction line
                print(" " * 60, end='\r')
                print("\n⚠️  Still recording! Stopping recording first...")
                recorder.stop_recording()
                # Wait for all processing to finish before exiting
                time.sleep(1) 
            print("\n👋 Exiting program...")
            break
        elif char == ' ':
            if not recorder.is_recording:
                recorder.start_recording()
            else:
                recorder.stop_recording()
        elif ord(char) == 3: # Handle Ctrl+C to exit gracefully
            print("\n\nCtrl+C detected. Exiting...")
            if recorder.is_recording:
                recorder.stop_recording()
                time.sleep(1)
            break

if __name__ == "__main__":
    main()
