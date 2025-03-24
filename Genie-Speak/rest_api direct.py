import pyaudio
import wave
import base64
import requests
import json
import time
import io
import sys

# Replace with your Google Cloud Speech-to-Text API key
API_KEY = "AIzaSyCWedzaa8HNtH8pl-gpuYu04zkLEosqq2g"

def get_default_mic():
    p = pyaudio.PyAudio()
    try:
        default_host_api = p.get_default_host_api_info()
        default_mic_index = default_host_api.get('defaultInputDevice')
        
        if default_mic_index is not None:
            default_mic = p.get_device_info_by_index(default_mic_index)
            print(f"\nUsing default microphone: {default_mic.get('name')} (index: {default_mic_index})")
            p.terminate()
            return default_mic_index
        else:
            print("No default microphone found.")
            p.terminate()
            sys.exit(1)
            
    except Exception as e:
        print(f"Error finding default microphone: {e}")
        p.terminate()
        sys.exit(1)

def record_audio(mic_index, rate=16000, silence_timeout=3, max_duration=15):
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    input_device_index=mic_index,
                    frames_per_buffer=1024)
    
    print("Recording... (will stop after 3s of silence or 15s in total)")
    frames = []
    start_time = time.time()
    last_sound_time = time.time()

    while True:
        data = stream.read(1024, exception_on_overflow=False)
        frames.append(data)
        
        if is_sound(data):
            last_sound_time = time.time()
        
        if time.time() - last_sound_time > silence_timeout:
            print("Silence detected. Stopping recording.")
            break
        if time.time() - start_time > max_duration:
            print("Maximum recording duration reached. Stopping recording.")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()

    audio_data = b"".join(frames)
    
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(audio_data)
    
    return wav_buffer.getvalue()

def is_sound(data, threshold=500):
    audio_data = wave.struct.unpack("%dh" % (len(data) // 2), data)
    max_amplitude = max(audio_data)
    return max_amplitude > threshold

def transcribe_audio_data(audio_data, api_key):
    audio_content = base64.b64encode(audio_data).decode("utf-8")

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 16000,
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
            for res in result["results"]:
                print(f"Transcript: {res['alternatives'][0]['transcript']}")
        else:
            print("No transcription results were found.")
    except requests.exceptions.RequestException as e:
        print(f"Error during transcription: {e}")
    except json.JSONDecodeError:
        print("Error decoding the response from the API.")

def main():
    mic_index = get_default_mic()
    audio_data = record_audio(mic_index)
    transcribe_audio_data(audio_data, API_KEY)

if __name__ == "__main__":
    main()
