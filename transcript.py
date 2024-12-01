import os
import json
import logging
from dataclasses import dataclass
from enum import Enum
import threading
from typing import Optional
import torchaudio
from transformers import pipeline as transformers_pipeline, AutoModelForSpeechSeq2Seq, AutoTokenizer, AutoFeatureExtractor
from huggingface_hub import login
from pyannote.audio import Pipeline
import numpy as np
from tqdm import tqdm
import torch
import datetime

class TranscriptionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TranscriptionResult:
    video_name: str
    status: TranscriptionStatus
    full_transcript: Optional[str] = None
    diarized_segments: Optional[list] = None
    error: Optional[str] = None

class TranscriptionManager:
    def __init__(self):
        self.transcriptions = {}
        self._load_auth_token()
        self._initialize_models()
        
    def _load_auth_token(self):
        token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
        with open(token_path, 'r') as token_file:
            self.auth_token = json.load(token_file)["HUGGING_FACE_TOKEN"]
        login(self.auth_token)

    def _initialize_models(self):
        self.model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model")
        os.makedirs(self.model_dir, exist_ok=True)

        # Initialize Whisper model
        whisper_model = "openai/whisper-tiny"
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            whisper_model, 
            cache_dir=self.model_dir, 
            use_auth_token=self.auth_token
        )
        tokenizer = AutoTokenizer.from_pretrained(
            whisper_model, 
            cache_dir=self.model_dir, 
            use_auth_token=self.auth_token
        )
        feature_extractor = AutoFeatureExtractor.from_pretrained(
            whisper_model, 
            cache_dir=self.model_dir, 
            use_auth_token=self.auth_token
        )

        self.transcription_pipeline = transformers_pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=tokenizer,
            feature_extractor=feature_extractor
        )

        # Initialize Diarization pipeline
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            cache_dir=self.model_dir,
            use_auth_token=self.auth_token,
        )

    def start_transcription(self, video_path: str) -> str:
        """Start the transcription process for a video file"""
        try:
            video_name = os.path.basename(video_path)
            logging.info(f"Initializing transcription for {video_name}")
            
            # Create initial transcription result
            self.transcriptions[video_name] = TranscriptionResult(
                video_name=video_name,
                status=TranscriptionStatus.PENDING
            )

            # Start transcription in a separate thread
            thread = threading.Thread(
                target=self._process_transcription,
                args=(video_path,),
                name=f"transcription-{video_name}"
            )
            thread.daemon = True  # Make thread daemon so it doesn't block program exit
            thread.start()
            
            logging.info(f"Transcription thread started for {video_name}")
            return video_name
        except Exception as e:
            logging.error(f"Error starting transcription: {e}")
            raise

    def _process_transcription(self, video_path: str):
        """Process the transcription in a background thread"""
        video_name = os.path.basename(video_path)
        print(f"\nStarting transcription for {video_name}")
        
        try:
            self.transcriptions[video_name].status = TranscriptionStatus.PROCESSING
            
            # Convert video to audio if needed
            try:
                print("Converting video to audio...")
                audio_path = self._ensure_audio_file(video_path)
            except Exception as e:
                raise Exception(f"Failed to convert video to audio: {str(e)}")
            
            try:
                print("Loading audio file...")
                audio, sample_rate = torchaudio.load(audio_path)
                
                # Convert stereo to mono if necessary
                if audio.shape[0] > 1:
                    print("Converting stereo to mono...")
                    audio = torch.mean(audio, dim=0, keepdim=True)
                
            except Exception as e:
                raise Exception(f"Failed to load audio file: {str(e)}")
            
            # Process in chunks
            chunk_duration = 30  # seconds
            total_duration = audio.shape[1] / sample_rate
            num_chunks = int(np.ceil(audio.shape[1] / (chunk_duration * sample_rate)))
            
            print(f"Processing {num_chunks} chunks...")
            full_transcription = ""
            
            for i in range(num_chunks):
                progress = (i + 1) / num_chunks * 100
                print(f"Transcription progress: {progress:.1f}%")
                
                start_sample = i * chunk_duration * sample_rate
                end_sample = min((i + 1) * chunk_duration * sample_rate, audio.shape[1])
                audio_chunk = audio[:, start_sample:end_sample].squeeze().numpy()
                
                transcription = self.transcription_pipeline(
                    audio_chunk, 
                    return_timestamps=True
                )['text']
                full_transcription += transcription

            # After successful transcription, save to file
            transcript_dir = os.path.join(os.path.dirname(video_path), 'transcripts')
            os.makedirs(transcript_dir, exist_ok=True)
            
            transcript_path = os.path.join(transcript_dir, f"{video_name}_transcript.json")
            
            transcript_data = {
                'video_name': video_name,
                'full_transcript': full_transcription,
                'timestamp': str(datetime.datetime.now()),
                'status': TranscriptionStatus.COMPLETED.value
            }
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)

            # Update transcription result
            self.transcriptions[video_name].status = TranscriptionStatus.COMPLETED
            self.transcriptions[video_name].full_transcript = full_transcription
            print(f"\nTranscription completed and saved for {video_name}")

        except Exception as e:
            error_msg = f"Transcription failed for {video_name}: {str(e)}"
            print(f"\nError: {error_msg}")
            logging.error(error_msg)
            self.transcriptions[video_name].status = TranscriptionStatus.FAILED
            self.transcriptions[video_name].error = str(e)

    def _ensure_audio_file(self, video_path: str) -> str:
        """Convert video to audio if needed"""
        try:
            import moviepy.editor as mp
            
            # Generate output path
            audio_path = os.path.splitext(video_path)[0] + '.wav'
            
            # Convert only if audio file doesn't exist
            if not os.path.exists(audio_path):
                logging.info(f"Converting video to audio: {video_path}")
                video = mp.VideoFileClip(video_path)
                video.audio.write_audiofile(audio_path)
                video.close()
                logging.info(f"Audio conversion completed: {audio_path}")
            
            return audio_path
        except Exception as e:
            logging.error(f"Error converting video to audio: {e}")
            raise

    def _extract_text_for_segment(self, full_text: str, start_time: float, 
                                end_time: float, total_duration: float) -> str:
        """Extract the relevant portion of text for a time segment"""
        text_length = len(full_text)
        start_idx = int((start_time / total_duration) * text_length)
        end_idx = int((end_time / total_duration) * text_length)
        return full_text[start_idx:end_idx].strip()

    def get_transcription_status(self, video_name: str) -> TranscriptionResult:
        """Get the current status of a transcription"""
        return self.transcriptions.get(video_name) 