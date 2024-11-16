import os
import json
import numpy as np
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import torchaudio
from tqdm import tqdm
from transformers import pipeline as transformers_pipeline, AutoModelForSpeechSeq2Seq, AutoTokenizer, AutoFeatureExtractor
from huggingface_hub import login

token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
with open(token_path, 'r') as token_file:
    auth_token = json.load(token_file)["HUGGING_FACE_TOKEN"]
login(auth_token)

model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
os.makedirs(model_dir, exist_ok=True)
audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_audio.wav")
cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diarization_cache.json")

diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    cache_dir=model_dir,
    use_auth_token=auth_token,
)

whisper_model = "openai/whisper-tiny"
model = AutoModelForSpeechSeq2Seq.from_pretrained(whisper_model, cache_dir=model_dir, use_auth_token=auth_token)
tokenizer = AutoTokenizer.from_pretrained(whisper_model, cache_dir=model_dir, use_auth_token=auth_token)
feature_extractor = AutoFeatureExtractor.from_pretrained(whisper_model, cache_dir=model_dir, use_auth_token=auth_token)

transcription_pipeline = transformers_pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=tokenizer,
    feature_extractor=feature_extractor
)

if os.path.exists(cache_path):
    with open(cache_path, 'r') as f:
        diarization_data = json.load(f)
else:
    with ProgressHook() as hook:
        print("Performing diarization:")
        diarization = diarization_pipeline(audio_path, hook=hook, num_speakers=2)
    diarization_data = [
        {"start": turn.start, "end": turn.end, "speaker": speaker}
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
    with open(cache_path, 'w') as f:
        json.dump(diarization_data, f)

# Load the full audio once
full_audio, sample_rate = torchaudio.load(audio_path)

# Split the audio into chunks for transcription
chunk_duration = 30  # seconds
num_chunks = int(np.ceil(full_audio.shape[1] / (chunk_duration * sample_rate)))

# Transcribe the audio in chunks with progress bar
print("Transcribing the full audio file in chunks:")
full_transcription = ""
for i in tqdm(range(num_chunks), desc="Transcribing", unit="chunk"):
    start_sample = i * chunk_duration * sample_rate
    end_sample = min((i + 1) * chunk_duration * sample_rate, full_audio.shape[1])
    audio_chunk = full_audio[:, start_sample:end_sample].squeeze().numpy()
    transcription = transcription_pipeline(audio_chunk, return_timestamps=True)['text']
    full_transcription += transcription

# Function to map time to text index
def time_to_text_index(time, sample_rate, full_transcription):
    # Assuming the transcription is evenly distributed, calculate the index
    total_samples = full_audio.shape[1]
    total_duration = total_samples / sample_rate
    text_length = len(full_transcription)
    return int((time / total_duration) * text_length)

# Process diarization data
segments = []
segment_infos = []

for segment_info in tqdm(diarization_data, desc="Processing segments", unit="segment"):
    start_time = segment_info["start"]
    end_time = segment_info["end"]
    speaker = segment_info["speaker"]

    start_index = time_to_text_index(start_time, sample_rate, full_transcription)
    end_index = time_to_text_index(end_time, sample_rate, full_transcription)
    segment_text = full_transcription[start_index:end_index]

    segments.append(segment_text)
    segment_infos.append(segment_info)

def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes}m {seconds:.1f}s"

# Print the transcriptions for each segment
for segment_info, segment_text in zip(segment_infos, segments):
    start_time = segment_info["start"]
    end_time = segment_info["end"]
    speaker = segment_info["speaker"]

    print(f"{seconds_to_min_sec(start_time)}s - {seconds_to_min_sec(end_time)}s: Speaker {speaker}")
    print(f"Transcription: {segment_text}\n")
