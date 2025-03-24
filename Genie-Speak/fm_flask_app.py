from flask import Flask, render_template_string, jsonify
from audio_transcriber import AudioTranscriber
from voice_output import VoiceOutput
from genie_interaction import GenieClient, GenieError, DEFAULT_ACCESS_TOKEN, DEFAULT_SPACE_ID, BASE_URL
import threading
import time
import os

app = Flask(__name__, static_url_path='/static')

# Create the static directory if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

# Global variables
current_state = "idle"
current_response = "Click on mic to start"
current_transcript = ""
is_processing = False

# Initialize components globally
transcriber = None
speaker = None
genie = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Voice Assistant</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f7f7f7;
            color: #444;
        }
        
        .container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 20px;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .status-container {
            position: relative;
            margin-bottom: 15px;
        }
        
        .status {
            text-align: center;
            padding: 18px;
            background: linear-gradient(135deg, #9370d8 0%, #3498DB 100%);
            color: #fff;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.07);
            font-size: 1.25em;
            font-weight: 500;
            letter-spacing: 0.5px;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }
        
        .exit-button {
            position: absolute;
            top: 50%;
            right: 15px;
            transform: translateY(-50%);
            background: #E74C3C; /* Flat UI Red */
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            font-weight: 500;
            z-index: 10;
        }
        
        .exit-button:hover {
            background: #C0392B; /* Darker Flat UI Red for hover */
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        /* Animation for the "consulting" state */
        @keyframes consulting {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .status.consulting {
            background: linear-gradient(270deg, #9370d8, #3498DB, #9370d8);
            background-size: 200% 200%;
            animation: consulting 2s ease infinite;
        }
        
        /* Container for the mic icon, styled to match speaker container size */
        .mic-container {
            width: 100px;
            height: 100px;
            position: relative;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Changed mic styling to match speaker styling exactly */
        .mic {
            width: 100px; /* Match the size of the speaker svg */
            height: 100px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }
        
        .mic.pressed {
            transform: scale(0.95);
        }
        
        /* Custom mic icon sized exactly like speaker */
        .mic-icon-img {
            width: 100px; /* Exactly match speaker icon size */
            height: 100px;
            object-fit: contain;
            transition: transform 0.2s ease;
        }
        
        /* Push effect when pressed */
        .mic.pressed .mic-icon-img {
            transform: scale(0.9);
        }
        
        /* Listening and used states adjusted for flat icon */
        .mic.listening {
            filter: drop-shadow(0 0 8px rgba(46, 204, 113, 0.8));
        }
        
        .mic.used {
            filter: drop-shadow(0 0 8px rgba(231, 76, 60, 0.8));
        }
        
        .speaker-container {
            width: 100px;
            height: 100px;
            position: relative;
        }
        
        .speaker {
            width: 100%;
            height: 100%;
            border-radius: 10px;
            background: #3498DB; /* Flat UI Blue */
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            box-shadow: 0 4px 10px rgba(52, 152, 219, 0.4);
        }
        
        .waveform {
            flex-grow: 1;
            height: 100px;
            margin-left: 20px;
            background: #f8f8f8;
            position: relative;
            overflow: hidden;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            padding: 15px;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.03);
        }
        
        .wave {
            position: absolute;
            height: 100%;
            width: 100%;
            background: linear-gradient(180deg, transparent 0%, #3498DB 50%, transparent 100%); /* Flat UI Blue */
            animation: wave 1s ease-in-out infinite;
            opacity: 0;
        }
        
        .wave.active {
            opacity: 0.5;
        }
        
        .transcript {
            position: relative;
            z-index: 1;
            color: #444;
            font-size: 0.95em;
            margin-top: auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 8px 12px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            min-height: 1.2em; /* Ensure consistent height even when empty */
            transition: opacity 0.3s ease;
        }
        
        @keyframes wave {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
    </style>
</head>
<body>
    <div class="status-container">
        <div class="status" id="status">Click on Genie icon to start</div>
        <button class="exit-button" onclick="exitApp()">Exit</button>
    </div>
    
    <div class="container">
        <div class="mic-container" id="micContainer">
            <div class="mic" id="mic">
                <!-- Load the icon from static folder - same size as speaker icon -->
                <img class="mic-icon-img" src="/static/icon.png" alt="Microphone">
            </div>
        </div>
        
        <div class="speaker-container" id="speakerContainer" style="display: none;">
            <div class="speaker" id="speaker">
                <svg id="speakerIcon" width="50" height="50" viewBox="0 0 24 24">
                    <path fill="white" d="M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.84 14,18.7V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16C15.5,15.29 16.5,13.76 16.5,12M3,9V15H7L12,20V4L7,9H3Z" />
                </svg>
            </div>
        </div>
        
        <div class="waveform">
            <div class="wave" id="wave"></div>
            <div class="transcript" id="transcript"></div>
        </div>
    </div>

    <script>
        // Client-side flag to track processing status
        let isClientProcessing = false;
        
        const micContainer = document.getElementById('micContainer');
        const micElement = document.getElementById('mic');
        const statusElement = document.getElementById('status');
        
        // Mouse and touch event listeners for visual feedback
        micContainer.addEventListener('mousedown', function() {
            micElement.classList.add('pressed');
        });
        
        micContainer.addEventListener('mouseup', function() {
            micElement.classList.remove('pressed');
            startRecording();
        });
        
        micContainer.addEventListener('mouseleave', function() {
            micElement.classList.remove('pressed');
        });
        
        micContainer.addEventListener('touchstart', function() {
            micElement.classList.add('pressed');
        });
        
        micContainer.addEventListener('touchend', function() {
            micElement.classList.remove('pressed');
            startRecording();
        });
        
        function startRecording() {
            // Only allow starting if not already processing
            if (!isClientProcessing) {
                console.log('Starting recording...');
                isClientProcessing = true;
                
                // Update UI immediately to show feedback
                statusElement.textContent = 'Starting...';
                
                fetch('/start_session')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Start session response:', data);
                        if (data.status === 'started') {
                            checkStatus();
                        } else {
                            console.log('Server rejected start request:', data.status);
                            isClientProcessing = false;
                            statusElement.textContent = 'Click on mic to start';
                        }
                    })
                    .catch(error => {
                        console.error('Error starting session:', error);
                        isClientProcessing = false;
                        statusElement.textContent = 'Error. Click on mic to try again';
                    });
            } else {
                console.log('Already processing, ignoring click');
            }
        }
        
        function checkStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    console.log('Status update:', data);
                    updateUI(data.state, data.response, data.transcript);
                    
                    if (data.state !== 'idle') {
                        setTimeout(checkStatus, 500);
                    } else {
                        // Reset the client-side processing flag when the server is idle
                        isClientProcessing = false;
                    }
                })
                .catch(error => {
                    console.error('Error checking status:', error);
                    isClientProcessing = false;
                    statusElement.textContent = 'Error. Click on mic to try again';
                });
        }
        
        let previousState = '';
        
        function updateUI(state, response, transcript) {
            const micContainer = document.getElementById('micContainer');
            const speakerContainer = document.getElementById('speakerContainer');
            const waveElement = document.getElementById('wave');
            const transcriptElement = document.getElementById('transcript');
            
            console.log('Updating UI for state:', state);
            
            // Remove any previous animation class
            statusElement.classList.remove('consulting');
            
            // Update status text
            switch(state) {
                case 'listening':
                    statusElement.textContent = 'Listening to your voice';
                    micElement.className = 'mic listening'; // Make mic green
                    break;
                case 'transcribing':
                    statusElement.textContent = 'Transcribing...';
                    micElement.className = 'mic used'; // Make mic red
                    break;
                case 'processing':
                    statusElement.textContent = 'Consulting Genie...';
                    statusElement.classList.add('consulting'); // Add animation class
                    break;
                case 'speaking':
                    statusElement.textContent = 'Speaking response';
                    // Clear the transcript completely when speaking starts
                    transcriptElement.textContent = ' ';

                    break;
                case 'idle':
                    statusElement.textContent = response || 'Click on mic to continue';
                    micElement.className = 'mic'; // Reset mic color
                    
                    // If we just finished speaking (transitioning from speaking to idle)
                    // keep the transcript clear
                    if (previousState === 'speaking') {
                        transcriptElement.textContent = '';
                    }
                    break;
                default:
                    statusElement.textContent = response || 'Ready';
            }
            
            // Store the current state for next comparison
            previousState = state;
            
            // Show/hide mic and speaker
            if (state === 'speaking') {
                micContainer.style.display = 'none';
                speakerContainer.style.display = 'block';
            } else {
                micContainer.style.display = 'block';
                speakerContainer.style.display = 'none';
            }
            
            // Update waveform
            waveElement.className = 'wave' + 
                (state === 'listening' || state === 'speaking' ? ' active' : '');
                
            // Only show transcript during listening, transcribing, and processing states
            if ( state === 'transcribing' || state === 'processing') {
                if (transcript) {
                    transcriptElement.textContent = `👂 ${transcript}`;
                }
            } else {
                transcriptElement.textContent ='';
            }
        }
        
        function exitApp() {
            if (confirm('Are you sure you want to exit?')) {
                window.close();
                // Fallback if window.close() doesn't work
                document.body.innerHTML = '<div style="text-align: center; margin-top: 50px;">You can now close this window</div>';
            }
        }
    </script>
</body>
</html>
'''

# Replace with your Google Cloud Speech-to-Text API key
GSPEECH_API_KEY = "AIzaSyCWedzaa8HNtH8pl-gpuYu04zkLEosqq2g"

# Initialize our components just once at startup
def initialize_components():
    global transcriber, speaker, genie
    try:
        transcriber = AudioTranscriber(GSPEECH_API_KEY)
        speaker = VoiceOutput()
        genie = GenieClient(base_url=BASE_URL, access_token=DEFAULT_ACCESS_TOKEN, space_id=DEFAULT_SPACE_ID)
        print("Components initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing components: {e}")
        return False

# Check if icon.png exists in static folder, if not, save a warning
def check_icon_file():
    if not os.path.exists('static/icon.png'):
        print("\n⚠️ WARNING: The icon.png file was not found in the static folder.")
        print("Please save your icon as 'static/icon.png' before running this app.\n")

@app.route('/')
def index():
    # Make sure components are initialized when the page loads
    if transcriber is None:
        initialize_components()
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def get_status():
    global current_transcript
    return jsonify({
        'state': current_state,
        'response': current_response,
        'transcript': current_transcript
    })

@app.route('/start_session')
def start_session():
    global current_state, current_response, current_transcript, is_processing
    
    # Make sure components are initialized
    if transcriber is None:
        success = initialize_components()
        if not success:
            return jsonify({'status': 'error', 'message': 'Failed to initialize components'})
    
    # Prevent multiple simultaneous sessions
    if is_processing:
        print("Already processing, rejecting new request")
        return jsonify({'status': 'already_processing'})
    
    print("Starting new session")
    is_processing = True
    
    def process_audio():
        global current_state, current_response, current_transcript, is_processing
        
        try:
            print("Audio processing thread started")
            
            # Start listening immediately 
            current_state = "listening"
            print("Starting listening...")
            
            mic_index = transcriber.get_default_mic()
            print(f"Using microphone at index {mic_index}")
            
            audio_data = transcriber.record_audio(mic_index)
            print(f"Audio recorded, data size: {len(audio_data) if audio_data else 'None'}")
            
            # Transcribing
            current_state = "transcribing"
            print("Transcribing audio...")
            
            transcript = transcriber.transcribe_audio_data(audio_data)
            print(f"Transcription result: {transcript}")
            
            if transcript:
                current_transcript = transcript
                
                # Processing with Genie
                current_state = "processing"
                print("Processing with Genie...")
                
                try:
                    raw_result = genie.submit_prompt(transcript)
                    result_text = genie.parse_result(raw_result)
                    current_response = result_text
                    print(f"Got response from Genie: {result_text[:100]}...")
                    
                    # Speaking response
                    current_state = "speaking"
                    print("Speaking response...")
                    speaker.speak(result_text)
                    
                except (GenieError, TimeoutError) as e:
                    print(f"Genie error: {e}")
                    current_response = f"Error: {str(e)}"
                except Exception as e:
                    print(f"Unexpected error during processing: {e}")
                    current_response = f"Unexpected error: {str(e)}"
            else:
                print("Failed to transcribe audio")
                current_response = "Failed to transcribe audio."
            
            # Set the final state to idle with the prompt to continue
            current_state = "idle"
            current_response = "Click on mic to continue"
            print("Process completed, returning to idle state")
            
        except Exception as e:
            print(f"Exception in audio thread: {e}")
            current_state = "idle"
            current_response = f"Error: {str(e)}. Click on mic to try again."
        finally:
            # Always reset the processing flag when done
            is_processing = False
            print("Processing flag reset")
    
    # Start processing in background thread
    thread = threading.Thread(target=process_audio)
    thread.daemon = True  # Make thread exit when main thread exits
    thread.start()
    
    return jsonify({'status': 'started'})

if __name__ == '__main__':
    # Check for the icon file
    check_icon_file()
    
    # Initialize components before starting the server
    initialize_components()
    app.run(debug=True)