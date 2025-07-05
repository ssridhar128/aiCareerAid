import os
from groq import Groq
# import speechbrain
from pyAudioAnalysis import audioBasicIO, ShortTermFeatures
import numpy as np
import pyaudio 
import wave
import time
import threading

# from speechbrain.inference.interfaces import foreign_class

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000
CHUNK = 2048
UPLOAD_FOLDER = "uploads"
OUTPUT_FILENAME = os.path.join(UPLOAD_FOLDER, "answer.wav")
api_key = os.getenv("GROQ_API_KEY")

def audio_to_text(audio_path):
    client = Groq(api_key=api_key)
    filename = audio_path

    with open(filename, "rb") as file:
        chat_completion = client.audio.transcriptions.create(
            model="whisper-large-v3", 
            temperature=0,         # deterministic output
            response_format="verbose_json",
            file=file,
            language="en"
        )
        
        return chat_completion

# def emotion(audio_path):  
#     classifier = foreign_class(source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP", pymodule_file="custom_interface.py", classname="CustomEncoderWav2vec2Classifier")
#     out_prob, score, index, text_lab = classifier.classify_file(audio_path)
#     print(text_lab)
#     return text_lab

def audio_features(audio_path):
    # Load audio file (make sure it's WAV, mono)
    [Fs, x] = audioBasicIO.read_audio_file(audio_path)

    # If stereo, use only one channel
    if x.ndim > 1:
        x = x[:, 0]

    # Extract features with window=50ms and step=25ms
    F, f_names = ShortTermFeatures.feature_extraction(x, Fs, 0.050 * Fs, 0.025 * Fs)

    # Find indexes of features you want
    energy_idx = f_names.index('energy')
    zcr_idx = f_names.index('zcr')
    spectral_entropy_idx = f_names.index('spectral_entropy')

    # Extract those features across all frames
    energy = F[energy_idx, :]
    zcr = F[zcr_idx, :]
    spectral_entropy = F[spectral_entropy_idx, :]
    # Compute mean values as summary statistics
    mean_energy = np.mean(energy)
    mean_zcr = np.mean(zcr)
    mean_spectral_entropy = np.mean(spectral_entropy)
    return mean_energy, mean_zcr, mean_spectral_entropy

def groqInput(energy, zcr, entropy):   
    energyS = ""
    if (energy <= 0.003):
        energyS = "The candidate is whispering or mumbling theroughout the response"; 
    elif (energy > 0.003 and energy <= 0.01):
        energyS = "The candidate is tends to be whispering/mumbling or is quiet through out the response"
    elif (energy > 0.01 and energy <= 0.04):
        energyS = "The candidate had a normal conversation, however, in a few parts they were quiet"
    elif (energy > 0.04 and energy <= 0.1):
        energyS = "The candidate talked in loud voice, so they were passionate"
    else: 
        energyS = "The candidate tended to shout"

    entroS = ""
    if (entropy <= 1.3):
        entroS = "The candidate has a steady, tonal, almost flat response (monotone)"; 
    elif (entropy > 1.3 and entropy <= 2.3):
        entroS = "The candidate has a controlled and focused speech"
    elif (entropy > 2.3 and entropy <= 3.3):
        entroS = "The candidate is speaking in a normal tone for the most part"
    elif (entropy > 3.3 and entropy <= 4.5):
        entroS = "The candidate seems to vary in tone a lot"
    else: 
        entroS = "The candidate tone is completely unstructured"

    zcrS = ""
    if (zcr <= 0.1):
        zcrS = "Clear Speech means they spoke steady"; 
    elif (zcr <= 0.15):
        zcrS = "Somewhat messy means they spoke steady but with mix of shaking (a little nervous)"
    else:
        zcrS = "Very Unclear means not sure if they were speaking or if it was just noise from audio"
    
    return energyS, entroS, zcrS

def record():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels = CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    
    input("press ENTER to start recording.")
    print("Recording... Press ENTER again to stop")

    recording = True

    def stop_recording():
        nonlocal recording
        input()
        recording = False
        print("Stopping recording...")

    stopper_thread = threading.Thread(target=stop_recording)
    stopper_thread.start()

    while recording:
        data = stream.read(CHUNK)
        frames.append(data)


    stopper_thread.join()
    stream.stop_stream()
    stream.close()
    audio.terminate()

    waveFile = wave.open(OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audio.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(b''.join(frames))
    waveFile.close()

    return OUTPUT_FILENAME
