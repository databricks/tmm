import pyaudio
import wave
import base64
import requests
import json
import time
import io
import sys
import os
from dotenv import load_dotenv
from typing import Optional, Union, Dict, Any

# Load environment variables at module level
load_dotenv()

class AudioTranscriber:
    def __init__(self, api_key: str, sample_rate: int = 16000):
        """
        Initialize AudioTranscriber with Google Cloud Speech-to-Text API key
        
        Args:
            api_key: Google Cloud Speech-to-Text API key
            sample_rate: Audio sample rate in Hz (default 16000)
        """
        self.api_key = api_key
        self.sample_rate = sample_rate
        self.pyaudio = pyaudio.PyAudio()
        self.default_mic_index = self.get_default_mic()

    def get_default_mic(self) -> Optional[int]:
        """Get the default microphone index"""
        try:
            default_host_api = self.pyaudio.get_default_host_api_info()
            default_mic_index = default_host_api.get('defaultInputDevice')
            
            if default_mic_index is not None:
                default_mic = self.pyaudio.get_device_info_by_index(default_mic_index)
                print(f"\nUsing default microphone: {default_mic.get('name')} (index: {default_mic_index})")
                return default_mic_index
            else:
                print("No default microphone found.")
                return None
                
        except Exception as e:
            print(f"Error finding default microphone: {e}")
            return None

    def _is_sound(self, data: bytes, threshold: int = 500) -> bool:
        """
        Check if audio data contains sound above threshold
        
        Args:
            data: Audio data bytes
            threshold: Amplitude threshold (default 500)
        """
        audio_data = wave.struct.unpack("%dh" % (len(data) // 2), data)
        max_amplitude = max(audio_data)
        return max_amplitude > threshold

    def record_audio(self, 
                    mic_index: Optional[int] = None,
                    silence_timeout: int = 3,
                    max_duration: int = 15) -> Optional[bytes]:
        """
        Record audio from microphone
        
        Args:
            mic_index: Microphone device index (uses default if None)
            silence_timeout: Stop recording after silence duration in seconds
            max_duration: Maximum recording duration in seconds
            
        Returns:
            Recorded audio data as bytes, or None if recording failed
        """
        if mic_index is None:
            mic_index = self.default_mic_index
            
        if mic_index is None:
            print("No microphone available")
            return None

        try:
            stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=1024
            )
            
            print("Recording... (will stop after 3s of silence or 15s in total)")
            frames = []
            start_time = time.time()
            last_sound_time = time.time()

            while True:
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)
                
                if self._is_sound(data):
                    last_sound_time = time.time()
                
                if time.time() - last_sound_time > silence_timeout:
                    print("Silence detected. Stopping recording.")
                    break
                if time.time() - start_time > max_duration:
                    print("Maximum recording duration reached. Stopping recording.")
                    break

            stream.stop_stream()
            stream.close()

            audio_data = b"".join(frames)
            
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.pyaudio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data)
            
            return wav_buffer.getvalue()

        except Exception as e:
            print(f"Error recording audio: {e}")
            return None

    def transcribe_audio_data(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio data using Google Cloud Speech-to-Text
        
        Args:
            audio_data: Audio data bytes to transcribe
            
        Returns:
            Transcribed text, or None if transcription failed
        """
        if not audio_data:
            return None
            
        audio_content = base64.b64encode(audio_data).decode("utf-8")

        url = f"https://speech.googleapis.com/v1/speech:recognize?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": self.sample_rate,
                "languageCode": "en-US"
            },
            "audio": {
                "content": audio_content
            }
        }

        try:
            print("Transcribing...")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if "results" in result:
                transcripts = []
                for res in result["results"]:
                    transcript = res['alternatives'][0]['transcript']
                    transcripts.append(transcript)
                    print(f"Transcript: {transcript}")
                return " ".join(transcripts)
            else:
                print("No transcription results were found.")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error during transcription: {e}")
            return None
        except json.JSONDecodeError:
            print("Error decoding the response from the API.")
            return None

    def record_and_transcribe(self) -> Optional[str]:
        """
        Record audio and transcribe it in one step
        
        Returns:
            Transcribed text, or None if recording or transcription failed
        """
        audio_data = self.record_audio()
        if audio_data:
            return self.transcribe_audio_data(audio_data)
        return None

    def __del__(self):
        """Cleanup PyAudio on deletion"""
        if hasattr(self, 'pyaudio'):
            self.pyaudio.terminate()

# Example usage:
if __name__ == "__main__":
    API_KEY = os.getenv('GSPEECH_API_KEY')
    
    transcriber = AudioTranscriber(API_KEY)
    transcript = transcriber.record_and_transcribe()
    
    if transcript:
        print(f"\nFinal transcript: {transcript}")