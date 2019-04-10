import json
import pygame
import pyaudio
import wave
import glob
import time

import io
import os
from _datetime import datetime;
# Aiml chat bot imports
import aiml


# Imports the Google Cloud client library

from google.cloud import speech
from google.cloud import texttospeech
from google.cloud.speech import enums
from google.cloud.speech import types

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE =  16000          #44100
CHUNK = 1024
RECORD_SECONDS = 3
WAVE_OUTPUT_FILENAME = "temp_file.wav"

# The file we keep all our conversations in during this chat session
thenow = datetime.now().strftime("%Y%m%d%H%M%S")
sessionFileName = "session_data_" + thenow + ".txt"

# instantiate chat bot
BRAIN_FILE="brain.dump"
aimlKernel = aiml.Kernel()

if os.path.exists(BRAIN_FILE):
    print("Loading from brain file: " + BRAIN_FILE)
    aimlKernel.loadBrain(BRAIN_FILE)
else:
    print("Parsing aiml files")
    aimlKernel.bootstrap(learnFiles="std-startup.aiml", commands="load aiml b")
    print("Saving brain file: " + BRAIN_FILE)
    aimlKernel.saveBrain(BRAIN_FILE)

# Instantiates a speechRecognition_client
speechRecognition_client = speech.SpeechClient()

# config our google speech/text recognition engine
speechRecognition_config = types.RecognitionConfig(encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,sample_rate_hertz=SAMPLE_RATE,language_code='en-US')

texttospeech_client = texttospeech.TextToSpeechClient()

texttospeech_voice = texttospeech.types.VoiceSelectionParams(language_code='en-US',ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

texttospeech_audio_config = texttospeech.types.AudioConfig(audio_encoding=texttospeech.enums.AudioEncoding.LINEAR16)

# Initializes pygame and pyaudio
pygame.mixer.pre_init(SAMPLE_RATE, -16, CHANNELS, 2048) # setup mixer to avoid sound lag
pygame.mixer.init()
pygame.init()

while True:
    variable = input('Hit key to say something: ')
    # start Recording
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    
    print("started recording...")
    frames = []
    for i in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
        
    print("stopped recording")
    # stop Recording
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Lame, save audio to file, need to use in memory buffers, but my SSD is FAST
    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(SAMPLE_RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()
    
    #sound = pygame.mixer.Sound(WAVE_OUTPUT_FILENAME)
    #sound.play()

    # Loads previsouly sample audio from disk
    with io.open(WAVE_OUTPUT_FILENAME, 'rb') as audio_file:
        speechRecognition_audio = types.RecognitionAudio(content=audio_file.read())

    # Call google speech to text
    # Detects speech in the audio file
    response = speechRecognition_client.recognize(speechRecognition_config, speechRecognition_audio)

    # For each response, send to chat bot
    for result in response.results:
        
        print('Google Says: {}'.format(result.alternatives[0].transcript))

        # Peel out text from google
        what_google_said = result.alternatives[0].transcript

        # Send the google speech to text response to aiml bot
        aiml_response = aimlKernel.respond(what_google_said)

        print("Aiml says:",aiml_response)
        
        # Now send amil chat bot response back up to google for text the speech conversion
        input_text = texttospeech.types.SynthesisInput(text=aiml_response)

        # Lame, save audio to file, need to use in memory buffers, but my SSD is FAST
        google_audio_response = texttospeech_client.synthesize_speech(input_text, texttospeech_voice, texttospeech_audio_config)
        
        # Load back up to replay audio throught pyaudio
        with open('what_was_said_output.wav', 'wb') as out:
             out.write(google_audio_response.audio_content)

        # Load back in and play
        #wav_data = data[44:len(header_wav)] # start after header
        #sound = pygame.mixer.Sound(buffer=wav_data)
        #sound.play()

        sound = pygame.mixer.Sound('what_was_said_output.wav')
        sound.play()

        #Write out this sessions bot data along with google response for later re-learning
        session_data = aimlKernel.getSessionData()
    
        f = io.open(sessionFileName, 'w+')
        f.write("------------------------------------------------")
        f.write("Google Said {0}".format(what_google_said))
        f.write(str(session_data))
        f.write("------------------------------------------------")
        f.close()


