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
        diarization = diarization_pipeline(audio_path, hook=hook, num_speakers=2)
    diarization_data = [
        {"start": turn.start, "end": turn.end, "speaker": speaker}
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
    with open(cache_path, 'w') as f:
        json.dump(diarization_data, f)

# Load the full audio once
full_audio, sample_rate = torchaudio.load(audio_path)

segments = []
segment_infos = []

for segment_info in diarization_data:
    start_time = segment_info["start"]
    end_time = segment_info["end"]
    speaker = segment_info["speaker"]

    start_sample = int(start_time * sample_rate)
    end_sample = int(end_time * sample_rate)
    segment = full_audio[:, start_sample:end_sample]
    segment_np = segment.squeeze().numpy()
    segments.append(segment_np)
    segment_infos.append(segment_info)

# Transcribe segments with progress bar
transcriptions = []
print("Transcribing audio segments:")
for segment_np in tqdm(segments, desc="Transcribing", unit="segment"):
    transcription = transcription_pipeline(segment_np)
    transcriptions.append(transcription)

for segment_info, transcription in zip(segment_infos, transcriptions):
    start_time = segment_info["start"]
    end_time = segment_info["end"]
    speaker = segment_info["speaker"]

    print(f"{start_time:.1f}s - {end_time:.1f}s: Speaker {speaker}")
    print(f"Transcription: {transcription['text']}\n")

