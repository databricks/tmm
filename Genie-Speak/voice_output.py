from elevenlabs import ElevenLabs, stream
from typing import Optional
import os
import pyttsx3
from dotenv import load_dotenv

# Load environment variables
load_dotenv(verbose=True, override=True)


class VoiceOutput:
    def __init__(self):
        """
        Initialize VoiceOutput with ElevenLabs if available, otherwise use pyttsx3
        """
        self.eleven_api_key = os.getenv('ELEVEN_API_KEY')
        print(f"voice out ElevenLabs API Key: {self.eleven_api_key}")
        self.voice_id = os.getenv('ELEVEN_VOICE_ID', 'ErXwobaYiN019PkySvjV')
        self.model_id = "eleven_multilingual_v2"
        
        if self.eleven_api_key:
            try:
                self.client = ElevenLabs(api_key=self.eleven_api_key)
                self.using_elevenlabs = True
                print(f"Using ElevenLabs for voice output with API key: {self.eleven_api_key}")
            except Exception as e:
                print(f"Failed to initialize ElevenLabs: {e}")
                self.using_elevenlabs = False
        else:
            print("No ElevenLabs API key found, using pyttsx3 for voice output")
            self.using_elevenlabs = False

        # Initialize pyttsx3 engine if ElevenLabs is unavailable
        if not self.using_elevenlabs:
            try:
                self.engine = pyttsx3.init()
            except Exception as e:
                print(f"Failed to initialize pyttsx3: {e}")
                self.engine = None

    def speak(self, text: str, stability: float = 0.5, similarity_boost: float = 0.5) -> bool:
        """
        Convert text to speech using either ElevenLabs or pyttsx3
        
        Args:
            text: Text to speak
            stability: Voice stability (0-1, ElevenLabs only)
            similarity_boost: Voice similarity boost (0-1, ElevenLabs only)
            
        Returns:
            True if successful, False otherwise
        """
        if not text:
            print("No text provided for speech synthesis.")
            return False

        if self.using_elevenlabs:
            try:
                audio_stream = self.client.text_to_speech.convert_as_stream(
                    text=text,
                    voice_id=self.voice_id,
                    model_id=self.model_id,
                    voice_settings={
                        "stability": stability,
                        "similarity_boost": similarity_boost
                    }
                )
                stream(audio_stream)
                return True
            except Exception as e:
                print(f"ElevenLabs error: {e}, falling back to pyttsx3")
                return self._pyttsx3_tts(text)
        else:
            return self._pyttsx3_tts(text)

    def _pyttsx3_tts(self, text: str) -> bool:
        """
        Use pyttsx3 for text-to-speech
        """
        if not self.engine:
            print("pyttsx3 engine is not initialized.")
            return False

        try:
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"pyttsx3 error: {e}")
            return False

# Example usage
if __name__ == "__main__":
    speaker = VoiceOutput()
    test_text = "Hello! This is a test of the voice output system."
    success = speaker.speak(test_text)
    print("Speech playback completed" if success else "Speech playback failed")