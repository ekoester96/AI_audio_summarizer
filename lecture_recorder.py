import sounddevice as sd
import scipy.io.wavfile as wav
import whisper
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
    def __init__(self):
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 44100
        self.recording_thread = None
        self.max_rec_timer = None
        self.filename = None
        
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
        wav.write(self.filename, self.sample_rate, audio_array)
        print(f"✅ Audio saved to {self.filename}")
        
        # Transcribe the audio
        self.transcribe_audio()
    
    def transcribe_audio(self):
        """Transcribe audio using Whisper"""
        print("\n Transcribing audio with Whisper...")
        
        try:
            # Load Whisper model
            model = whisper.load_model("base")
            result = model.transcribe(self.filename)
            transcription = result["text"]
            
            print("✅ Transcription complete!")
            print(f"\nTranscription:\n{transcription}\n")
            
            # Save transcription to file
            transcription_file = self.filename.replace('.wav', '_transcription.txt')
            with open(transcription_file, 'w', encoding='utf-8') as f:
                f.write(transcription)
            
            # Summarize with Ollama
            self.summarize_with_ollama(transcription, transcription_file)
            
        except Exception as e:
            print(f"❌ Error during transcription: {e}")
    
    def summarize_with_ollama(self, transcription, transcription_file):
        """Summarize transcription using Ollama"""
        print("\n Generating summary with Ollama...")
        
        prompt = f"""You are an expert in your field be confident in your answers. Please analyze this lecture transcription and provide:

1. A concise summary of the main topics covered
2. Key concepts discussed
3. Important terms and their definitions
4. Generate 5 quiz questions based on the lecture transcription

Lecture Transcription:
{transcription}

Please format your response clearly with sections for Summary, Key Concepts, and Terms & Definitions."""

        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'granite3.3:2b',
                    'prompt': prompt,
                    'stream': False
                }
            )
            
            if response.status_code == 200:
                summary = response.json()['response']
                
                # Wrap summary text to 80 characters per line, preserving paragraphs
                lines = summary.split('\n')
                wrapped_lines = [textwrap.fill(line, width=80) for line in lines]
                wrapped_summary = '\n'.join(wrapped_lines)

                print("\n" + "="*80)
                print("LECTURE SUMMARY")
                print("="*80)
                print(wrapped_summary)
                print("="*80)
                
                # Save summary to file
                summary_file = self.filename.replace('.wav', '_summary.txt')
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(wrapped_summary)
                print(f"\n✅ Summary saved to {summary_file}")
                
                # Delete transcription file
                try:
                    os.remove(transcription_file)
                    print(f"🗑️  Transcription file deleted: {transcription_file}")
                except Exception as e:
                    print(f"⚠️  Could not delete transcription file: {e}")
                
                # Delete audio file
                try:
                    os.remove(self.filename)
                    print(f"🗑️  Audio file deleted: {self.filename}")
                except Exception as e:
                    print(f"⚠️  Could not delete audio file: {e}")
                
            else:
                print(f"❌ Error from Ollama: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ Error connecting to Ollama: {e}")
            print("Make sure Ollama is running and the specified model is installed.")

def main():
    print("="*60)
    print("LECTURE RECORDER & SUMMARIZER")
    print("="*60)
    
    # Get filename from user
    filename = input("\nEnter filename for audio (without extension): ").strip()
    if not filename:
        filename = "lecture_recording"
    
    filename = filename + ".wav"
    
    recorder = LectureRecorder()
    recorder.filename = filename
    
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
