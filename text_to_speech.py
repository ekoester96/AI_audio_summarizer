import sounddevice as sd
import scipy.io.wavfile as wav
from scipy.signal import resample
import subprocess
import requests
import threading
import numpy as np
import os
import sys
import textwrap
import time
import readchar
import queue
import tempfile
from piper import PiperVoice
from huggingface_hub import hf_hub_download

MODEL_PATH = ""
LLM_MODEL = "gemma3:4b"
# Download Piper voice model from Hugging Face
PIPER_VOICE_PATH = hf_hub_download(repo_id="rhasspy/piper-voices", filename="es_ES-carlfm-x_low.onnx", subfolder="es/es_ES/carlfm/x_low")
json_path = hf_hub_download(repo_id="rhasspy/piper-voices", filename="es_ES-carlfm-x_low.onnx.json", subfolder="es/es_ES/carlfm/x_low")

class RealtimeTranslator:
    def __init__(self, model_path: str = MODEL_PATH, voice_path: str = PIPER_VOICE_PATH):
        self.is_running = False
        self.sample_rate = 44100
        self.target_sample_rate = 16000
        self.chunk_duration = 2  # seconds
        self.audio_queue = queue.Queue()
        self.model_path = model_path
        
        # Setup whisper.cpp path
        whisper_cpp_dir = os.path.dirname(os.path.dirname(model_path))
        self.binary_path = os.path.join(whisper_cpp_dir, "build", "bin", "whisper-cli")
        
        # Load Piper voice model
        print("🔊 Loading Piper TTS voice model...")
        try:
            self.voice = PiperVoice.load(voice_path)
            print("✅ Piper voice loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load Piper voice: {e}")
            sys.exit(1)
        
        # Verify paths
        if not os.path.exists(self.binary_path):
            print(f"❌ Binary not found: {self.binary_path}")
            sys.exit(1)
        if not os.path.exists(self.model_path):
            print(f"❌ Model not found: {self.model_path}")
            sys.exit(1)
    
    def start(self):
        """Start real-time translation"""
        if self.is_running:
            return
        
        self.is_running = True
        print("\n🎤 Real-time translation started (English → Spanish)")
        print("📢 Start speaking... Press 'q' to quit\n")
        print("=" * 80)
        
        # Start recording thread
        self.recording_thread = threading.Thread(target=self._record_chunks)
        self.recording_thread.start()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_chunks)
        self.processing_thread.start()
    
    def _record_chunks(self):
        """Record audio in 2-second chunks"""
        chunk_samples = int(self.sample_rate * self.chunk_duration)
        
        def callback(indata, frames, time, status):
            if status:
                print(f"⚠️  Audio status: {status}", file=sys.stderr)
            if self.is_running:
                # Add chunk to queue when we have enough samples
                self.audio_queue.put(indata.copy())
        
        with sd.InputStream(
            samplerate=self.sample_rate, 
            channels=1, 
            callback=callback,
            blocksize=chunk_samples
        ):
            while self.is_running:
                sd.sleep(100)
    
    def _process_chunks(self):
        """Process audio chunks from queue"""
        while self.is_running:
            try:
                # Get audio chunk from queue (with timeout to check is_running)
                audio_chunk = self.audio_queue.get(timeout=0.5)
                
                # Transcribe the chunk
                transcription = self._transcribe_chunk(audio_chunk)
                
                if transcription and '[BLANK_AUDIO]' not in transcription:
                    # Translate the transcription
                    translation = self._translate_text(transcription)
                    
                    if translation:
                        # Print with text wrapping
                        self._print_translation(transcription, translation)
                        
                        # Speak the translation using Piper
                        self._speak_translation(translation)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"\n⚠️  Error processing chunk: {e}")
    
    def _transcribe_chunk(self, audio_chunk):
        """Transcribe a single audio chunk using whisper.cpp"""
        tmp_filename = None
        try:
            # Create temporary file for this chunk
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_filename = tmp_file.name
            
            # Resample and save chunk
            audio_array = audio_chunk.flatten()
            num_samples = int(len(audio_array) * self.target_sample_rate / self.sample_rate)
            audio_resampled = resample(audio_array, num_samples)
            audio_int16 = (audio_resampled * 32767).astype(np.int16)
            wav.write(tmp_filename, self.target_sample_rate, audio_int16)
            
            # Run whisper.cpp
            cmd = [
                self.binary_path,
                "-f", tmp_filename,
                "-m", self.model_path,
                "-l", "en",
                "-t", "4",
                "-nt",
            ]
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Clean up temp file
            os.remove(tmp_filename)
            
            transcription = result.stdout.strip()
            return transcription if transcription else None
            
        except subprocess.TimeoutExpired:
            print("\n⚠️  Transcription timeout")
            if tmp_filename and os.path.exists(tmp_filename):
                os.remove(tmp_filename)
            return None
        except Exception as e:
            if tmp_filename and os.path.exists(tmp_filename):
                os.remove(tmp_filename)
            return None
    
    def _translate_text(self, text):
        """Translate English text to Spanish using Ollama"""
        try:
            prompt = f"""Translate the following English text to Spanish. Only provide the Spanish translation, nothing else.

English: {text}

Spanish:"""
            
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': LLM_MODEL,
                    'prompt': prompt,
                    'stream': False
                },
                timeout=10
            )
            response.raise_for_status()
            
            translation = response.json()['response'].strip()
            return translation
            
        except requests.exceptions.RequestException as e:
            print(f"\n⚠️  Translation error: {e}")
            return None
        except Exception as e:
            return None
    
    def _speak_translation(self, text):
        """Convert Spanish text to speech using Piper and play it"""
        try:
            # Use synthesize which returns a generator of AudioChunk objects
            audio_chunks = []
            for audio_chunk in self.voice.synthesize(text):
                # Get the 16-bit PCM audio bytes from the AudioChunk
                audio_chunks.append(audio_chunk.audio_int16_bytes)
            
            # Combine all chunks
            audio_bytes = b''.join(audio_chunks)
            
            # Convert bytes to numpy array (PCM 16-bit audio)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Get sample rate from the AudioChunk (all chunks have same rate)
            # We'll use 16000 as shown in the debug output, or get from config
            sample_rate = self.voice.config.sample_rate
            
            # Play the audio
            sd.play(audio_array, sample_rate)
            sd.wait()  # Wait until audio finishes playing
            
        except Exception as e:
            print(f"\n⚠️  TTS error: {e}")
            import traceback
            traceback.print_exc()
    
    def _print_translation(self, original, translation):
        """Print translation with text wrapping"""
        # Wrap text to 80 characters
        # wrapped_original = textwrap.fill(f"🇺🇸 {original}", width=80, subsequent_indent="   ")
        wrapped_translation = textwrap.fill(f"🇪🇸 {translation}", width=80, subsequent_indent="   ")
        
        # print(wrapped_original)
        print(wrapped_translation)
        print("-" * 80)

    def stop(self):
        """Stop translation"""
        if not self.is_running:
            return
        
        print("\n\n🛑 Stopping translation...")
        self.is_running = False
        
        # Wait for threads to finish
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join()
        
        print("✅ Translation stopped")


def main():
    print("=" * 80)
    print("REAL-TIME ENGLISH → SPANISH TRANSLATOR WITH TTS")
    print("=" * 80)
    print("\nUsing whisper.cpp for transcription, Ollama for translation, and Piper for TTS")
    print(f"Model: {LLM_MODEL}")
    print("\nMake sure Ollama is running: ollama serve")
    print(f"Make sure {LLM_MODEL} is installed: ollama pull {LLM_MODEL}")
    
    translator = RealtimeTranslator()
    
    print("\nPress SPACE to start, 'q' to quit...")
    
    started = False
    
    while True:
        key = readchar.readkey()
        
        if key.lower() == 'q':
            if started:
                translator.stop()
            print("\n👋 Exiting program...")
            break
        elif key == ' ' and not started:
            translator.start()
            started = True


if __name__ == "__main__":
    main()
