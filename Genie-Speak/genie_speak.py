from audio_transcriber import AudioTranscriber
from voice_output import VoiceOutput
from genie_interaction import GenieClient, GenieError, DEFAULT_ACCESS_TOKEN, DEFAULT_SPACE_ID, BASE_URL
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API key from environment
GSPEECH_API_KEY = os.getenv('GSPEECH_API_KEY')

def main():
    transcriber = AudioTranscriber(GSPEECH_API_KEY)
    mic_index = transcriber.get_default_mic()

    should_continue = True
    
    while should_continue: 
        audio_data = transcriber.record_audio(mic_index)
        transcript = transcriber.transcribe_audio_data(audio_data)
        speaker = VoiceOutput()
        genie = GenieClient(base_url=BASE_URL,access_token=DEFAULT_ACCESS_TOKEN,space_id=DEFAULT_SPACE_ID)

        if transcript:
            
            try:
                raw_result = genie.submit_prompt(transcript)
                result_text = genie.parse_result(raw_result)
                print(f"\nGenie Response: {result_text}")
            except GenieError as e:
                print(f"\nError: {str(e)}")
            except TimeoutError:
                print("\nRequest timed out. Try increasing max_wait_seconds.")
            except Exception as e:
                print(f"\nUnexpected error: {str(e)}")
        else:
            print("Failed to transcribe audio.")
        # use the ElevenLabsSpeaker class to speak the response
        speaker.speak(result_text)

        # Check if the user wants to continue
        should_continue = input("Do you want to continue? (Y/n): ").strip().lower() != 'n'
        if not should_continue:
            print("Exiting...")
            break    
    


if __name__ == "__main__":
    main()