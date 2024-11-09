import os
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from huggingface_hub import login

auth_token = "[API_KEY]"

model_dir = "/Users/nickkleinsasser/Documents/SpeakerDiarization/model"
audio_path = "/Users/nickkleinsasser/Documents/SpeakerDiarization/output_audio.wav"

os.makedirs(model_dir, exist_ok=True)

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1", 
    cache_dir=model_dir,
    use_auth_token=auth_token,
)

with ProgressHook() as hook:
    diarization = pipeline(audio_path, hook=hook)  #, num_speakers=2)  # Maybe?

for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"{turn.start:.1f}s - {turn.end:.1f}s: Speaker {speaker}")
