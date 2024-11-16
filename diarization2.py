import os
import json
import numpy as np
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import torchaudio
from tqdm import tqdm
from transformers import pipeline as transformers_pipeline, AutoModelForSpeechSeq2Seq, AutoTokenizer, AutoFeatureExtractor
from huggingface_hub import login

# Load Hugging Face token
token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
with open(token_path, 'r') as token_file:
    auth_token = json.load(token_file)["HUGGING_FACE_TOKEN"]
login(auth_token)

# Set up directories and paths
model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
os.makedirs(model_dir, exist_ok=True)
audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_audio.wav")
cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diarization_cache.json")

# Load diarization pipeline
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    cache_dir=model_dir,
    use_auth_token=auth_token,
)

# Load Whisper model for transcription
whisper_model = "openai/whisper-small"
model = AutoModelForSpeechSeq2Seq.from_pretrained(whisper_model, cache_dir=model_dir, use_auth_token=auth_token)
tokenizer = AutoTokenizer.from_pretrained(whisper_model, cache_dir=model_dir, use_auth_token=auth_token)
feature_extractor = AutoFeatureExtractor.from_pretrained(whisper_model, cache_dir=model_dir, use_auth_token=auth_token)

transcription_pipeline = transformers_pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=tokenizer,
    feature_extractor=feature_extractor
)

# Load diarization data or compute it
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

# Load audio
full_audio, sample_rate = torchaudio.load(audio_path)

# Split the audio into overlapping chunks
chunk_duration = 30  # seconds
overlap_duration = 2  # seconds
num_chunks = int(np.ceil(full_audio.shape[1] / (chunk_duration * sample_rate)))

# Transcribe audio in chunks with overlap
print("Transcribing the full audio file in chunks:")
chunk_transcriptions = []
chunk_word_timestamps = []

for i in tqdm(range(num_chunks), desc="Transcribing", unit="chunk"):
    start_sample = max(0, i * chunk_duration * sample_rate - overlap_duration * sample_rate)
    end_sample = min((i + 1) * chunk_duration * sample_rate + overlap_duration * sample_rate, full_audio.shape[1])
    audio_chunk = full_audio[:, start_sample:end_sample].squeeze().numpy()

    try:
        transcription_result = transcription_pipeline(audio_chunk, return_timestamps=True)
        chunk_transcriptions.append(transcription_result['text'])
        chunk_word_timestamps.extend(transcription_result.get('chunks', []))
    except Exception as e:
        print(f"Transcription failed for chunk {i}: {e}")
        chunk_transcriptions.append("")

# Match diarization segments to transcription
segments = []
for segment_info in tqdm(diarization_data, desc="Processing segments", unit="segment"):
    start_time = segment_info["start"]
    end_time = segment_info["end"]
    speaker = segment_info["speaker"]

    # Get words within the segment
    words_in_segment = [
        word["text"] for word in chunk_word_timestamps
        if start_time <= word["timestamp"]["start"] < end_time
    ]
    segment_text = " ".join(words_in_segment)
    segments.append({"speaker": speaker, "start": start_time, "end": end_time, "text": segment_text})

# Utility function for time formatting
def seconds_to_min_sec(seconds):
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes}m {seconds:.1f}s"

# Print the diarized transcription
for segment in segments:
    start_time = segment["start"]
    end_time = segment["end"]
    speaker = segment["speaker"]
    text = segment["text"]

    print(f"{seconds_to_min_sec(start_time)}s - {seconds_to_min_sec(end_time)}s: Speaker {speaker}")
    print(f"Transcription: {text}\n")
