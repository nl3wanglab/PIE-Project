import os
import json
import numpy as np
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
import torchaudio
from transformers import pipeline as transformers_pipeline, AutoModelForSpeechSeq2Seq, AutoTokenizer, AutoFeatureExtractor
from huggingface_hub import login

# Hugging Face authentication
auth_token = "[API_KEY]"
login(auth_token)

# Define paths
model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
os.makedirs(model_dir, exist_ok=True)

model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_audio.wav")
model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diarization_cache.json")

# Load diarization model
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    cache_dir=model_dir,
    use_auth_token=auth_token,
)

# Load model components for transcription
model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-small", cache_dir=model_dir, use_auth_token=auth_token)
tokenizer = AutoTokenizer.from_pretrained("openai/whisper-small", cache_dir=model_dir, use_auth_token=auth_token)
feature_extractor = AutoFeatureExtractor.from_pretrained("openai/whisper-small", cache_dir=model_dir, use_auth_token=auth_token)

# Initialize the ASR pipeline with the locally cached model components
transcription_pipeline = transformers_pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=tokenizer,
    feature_extractor=feature_extractor
)

# Check if diarization is cached
if os.path.exists(cache_path):
    with open(cache_path, 'r') as f:
        diarization_data = json.load(f)
else:
    # Run speaker diarization with progress tracking and cache the results
    with ProgressHook() as hook:
        diarization = diarization_pipeline(audio_path, hook=hook)
    diarization_data = [
        {"start": turn.start, "end": turn.end, "speaker": speaker}
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
    with open(cache_path, 'w') as f:
        json.dump(diarization_data, f)

# Process each segment
for segment_info in diarization_data:
    start_time = segment_info["start"]
    end_time = segment_info["end"]
    speaker = segment_info["speaker"]

    # Load the specific segment from the audio file
    segment, _ = torchaudio.load(audio_path, frame_offset=int(start_time * 16000), num_frames=int((end_time - start_time) * 16000))

    # Convert segment to numpy array for compatibility with the transcription pipeline
    segment_np = segment.squeeze().numpy()

    # Transcribe without specifying sampling_rate in the pipeline call
    transcription = transcription_pipeline(segment_np)

    # Print the speaker and corresponding transcription
    print(f"{start_time:.1f}s - {end_time:.1f}s: Speaker {speaker}")
    print(f"Transcription: {transcription['text']}\n")

