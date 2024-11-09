import json
import os
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from huggingface_hub import login

token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
with open(token_path, 'r') as token_file:
    auth_token = json.load(token_file)["HUGGING_FACE_TOKEN"]

model_dir = "/Users/nickkleinsasser/Documents/SpeakerDiarization/model"
audio_path = "/Users/nickkleinsasser/Documents/SpeakerDiarization/output_audio.wav"

os.makedirs(model_dir, exist_ok=True)

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1", 
    cache_dir=model_dir,
    use_auth_token=auth_token,
)

with ProgressHook() as hook:
    diarization = pipeline(audio_path, hook=hook)

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}s - {turn.end:.1f}s: Speaker {speaker}")
