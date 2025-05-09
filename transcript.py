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
from pyannote.audio.pipelines.utils.hook import ProgressHook
import numpy as np
from tqdm import tqdm
import torch
import datetime
from pathlib import Path
import whisper

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
    def __init__(self, model_size="base"):
        self.model_size = model_size
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

        # Initialize device
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            self.device = torch.device("mps")
            logging.info("MPS backend is available. Using MPS.")
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
            logging.info("CUDA backend is available. Using CUDA.")
        else:
            self.device = torch.device("cpu")
            logging.info("Using CPU for processing.")

        # Initialize Whisper model cache
        self.whisper_models = {}
        # Don't load default model here - wait for first use

        # Initialize Diarization pipeline
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            cache_dir=self.model_dir,
            use_auth_token=self.auth_token,
        ).to(self.device)

    def _load_whisper_model(self, model_size):
        """Load a Whisper model if not already loaded"""
        if model_size not in self.whisper_models:
            logging.info(f"Loading Whisper model: {model_size}")
            self.whisper_models[model_size] = whisper.load_model(model_size)
            logging.info(f"Whisper model {model_size} loaded successfully")
        return self.whisper_models[model_size]

    def start_transcription(self, file_path, guid, use_diarization=False, model_size=None):
        """Start transcription with specified model"""
        try:
            # Check if transcription is already in progress
            if guid in self.transcriptions:
                current_status = self.transcriptions[guid].status
                if current_status in [TranscriptionStatus.PENDING, TranscriptionStatus.PROCESSING]:
                    logging.warning(f"Transcription already in progress for GUID: {guid}")
                    return
            
            # Use provided model size or fall back to default
            model = model_size or self.model_size
            
            # Ensure the requested model is loaded
            whisper_model = self._load_whisper_model(model)
            
            # Start transcription with the loaded model
            logging.info(f"Initializing transcription for GUID: {guid} with model: {model}, diarization: {use_diarization}")
            
            # Create initial transcription result
            self.transcriptions[guid] = TranscriptionResult(
                video_name=guid,
                status=TranscriptionStatus.PENDING
            )

            # Start transcription in a separate thread
            thread = threading.Thread(
                target=self._process_transcription,
                args=(file_path, guid, use_diarization, model),
                name=f"transcription-{guid}"
            )
            thread.daemon = True
            thread.start()
            
            logging.info(f"Transcription thread started for GUID: {guid}")
            
        except Exception as e:
            logging.error(f"Error starting transcription: {e}")
            raise

    def _process_transcription(self, file_path: str, guid: str, use_diarization: bool = False, model: str = "base"):
        """Process the transcription in a background thread"""
        print(f"\nStarting transcription for GUID: {guid}")
        
        try:
            self.transcriptions[guid].status = TranscriptionStatus.PROCESSING
            
            # Convert video to audio if needed
            audio_path = self._ensure_audio_file(file_path, guid)
            
            try:
                # Get the appropriate Whisper model
                whisper_model = self._load_whisper_model(model)
                
                # Use Whisper for transcription
                print("Starting Whisper transcription...")
                result = whisper_model.transcribe(
                    audio_path,
                    language="en",
                    task="transcribe",
                    verbose=True
                )
                
                # Format the results
                transcribed_segments = []
                for segment in result["segments"]:
                    transcribed_segments.append({
                        'text': segment['text'],
                        'timestamp': [segment['start'], segment['end']]
                    })

                # Create full transcript
                full_transcript = {
                    'text': result['text'],
                    'segments': transcribed_segments
                }

                # Save initial transcript
                transcript_dir = os.path.join(os.path.dirname(file_path), 'transcripts')
                os.makedirs(transcript_dir, exist_ok=True)
                transcript_path = os.path.join(transcript_dir, f"{guid}_transcript.json")
                
                transcript_data = {
                    'guid': guid,
                    'full_transcript': full_transcript['text'],
                    'segments': full_transcript['segments'],
                    'timestamp': str(datetime.datetime.now()),
                    'status': TranscriptionStatus.COMPLETED.value
                }
                
                # After transcription is complete, process diarization if requested
                if use_diarization:
                    try:
                        print("\nStarting diarization process...")
                        # Run diarization
                        with ProgressHook() as hook:
                            diarization = self.diarization_pipeline(audio_path, hook=hook)
                        
                        # Convert diarization results to segments
                        diarized_segments = []
                        for turn, _, speaker in diarization.itertracks(yield_label=True):
                            segment = {
                                "start": turn.start,
                                "end": turn.end,
                                "speaker": speaker,
                                "text": ""  # Will be filled with transcribed text
                            }
                            diarized_segments.append(segment)
                        
                        # Align transcribed text with diarization segments
                        for segment in diarized_segments:
                            segment_start = segment["start"]
                            segment_end = segment["end"]
                            
                            # Find transcribed text that falls within this segment's time range
                            segment_text = []
                            for trans_segment in transcribed_segments:
                                trans_start = trans_segment["timestamp"][0]
                                trans_end = trans_segment["timestamp"][1]
                                
                                # Check for overlap
                                if (trans_start <= segment_end and trans_end >= segment_start):
                                    segment_text.append(trans_segment["text"])
                        
                            segment["text"] = " ".join(segment_text)
                        
                        # Add diarized segments to transcript data
                        transcript_data['diarized_segments'] = diarized_segments
                        print("Diarization completed successfully")
                    
                    except Exception as e:
                        print(f"Error during diarization: {str(e)}")
                        logging.error(f"Diarization failed: {str(e)}")
                        # Continue with saving the transcript even if diarization fails
                
                # Save the final transcript
                print(f"Saving transcript to: {transcript_path}")
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)

                # Update transcription result
                self.transcriptions[guid].status = TranscriptionStatus.COMPLETED
                self.transcriptions[guid].full_transcript = full_transcript['text']
                self.transcriptions[guid].segments = full_transcript['segments']
                if use_diarization and 'diarized_segments' in transcript_data:
                    self.transcriptions[guid].diarized_segments = transcript_data['diarized_segments']
                
                print(f"\nTranscription and processing completed for GUID: {guid}")

            except Exception as e:
                error_msg = f"Transcription failed for GUID {guid}: {str(e)}"
                print(f"\nError: {error_msg}")
                logging.error(error_msg)
                self.transcriptions[guid].status = TranscriptionStatus.FAILED
                self.transcriptions[guid].error = str(e)

        except Exception as e:
            error_msg = f"Transcription failed for GUID {guid}: {str(e)}"
            print(f"\nError: {error_msg}")
            logging.error(error_msg)
            self.transcriptions[guid].status = TranscriptionStatus.FAILED
            self.transcriptions[guid].error = str(e)

    def _ensure_audio_file(self, file_path: str, guid: str) -> str:
        """Convert video to audio if needed"""
        try:
            import moviepy.editor as mp
            
            # Generate output path using GUID
            audio_path = os.path.join(os.path.dirname(file_path), f"{guid}.wav")
            
            # Convert only if audio file doesn't exist
            if not os.path.exists(audio_path):
                logging.info(f"Converting video to audio for GUID: {guid}")
                video = mp.VideoFileClip(file_path)
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

    def get_transcription_status(self, guid: str) -> Optional[TranscriptionResult]:
        """Get the current status of a transcription"""
        return self.transcriptions.get(guid)

    def get_transcript(self, guid: str) -> Optional[dict]:
        """Get the transcript data for a video if it exists"""
        try:
            print(f"\n=== Getting Transcript for GUID: {guid} ===")
            
            # Look for transcript in transcripts directory
            transcript_dir = os.path.join(UPLOAD_FOLDER, "transcripts")
            transcript_path = os.path.join(transcript_dir, f"{guid}_transcript.json")
            
            if os.path.exists(transcript_path):
                print(f"Found transcript file at {transcript_path}")
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                return transcript_data
            
            # If not found in file, check memory
            if guid in self.transcriptions:
                result = self.transcriptions[guid]
                if result.status == TranscriptionStatus.COMPLETED:
                    return {
                        'guid': guid,
                        'full_transcript': result.full_transcript,
                        'timestamp': str(datetime.datetime.now()),
                        'status': result.status.value
                    }
            
            print(f"No transcript found for GUID: {guid}")
            return None

        except Exception as e:
            logging.error(f"Error reading transcript for GUID {guid}: {str(e)}", exc_info=True)
            return None

    def process_diarization(self, guid: str):
        """Process diarization separately after transcription is complete"""
        try:
            # Get the existing transcript
            transcript_result = self.get_transcript(guid)
            if not transcript_result:
                raise Exception("Transcript not found")

            # Get the audio path
            audio_path = os.path.join(UPLOAD_FOLDER, f"{guid}.wav")
            if not os.path.exists(audio_path):
                raise Exception("Audio file not found")

            print("Starting diarization...")
            with ProgressHook() as hook:
                diarization = self.diarization_pipeline(audio_path, hook=hook)
            
            # Convert diarization results to segments
            diarized_segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = {
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                    "text": ""  # Will be filled with transcribed text
                }
                diarized_segments.append(segment)
            
            # Align transcribed text with diarization segments
            for segment in diarized_segments:
                segment_start = segment["start"]
                segment_end = segment["end"]
                
                # Find transcribed text that falls within this segment's time range
                segment_text = []
                for trans_segment in transcript_result['segments']:
                    trans_start = trans_segment["timestamp"][0]
                    trans_end = trans_segment["timestamp"][1]
                    
                    # Check for overlap
                    if (trans_start <= segment_end and trans_end >= segment_start):
                        segment_text.append(trans_segment["text"])
                
                segment["text"] = " ".join(segment_text)

            # Update the transcript file with diarization data
            transcript_path = os.path.join(UPLOAD_FOLDER, 'transcripts', f"{guid}_transcript.json")
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
            
            transcript_data['diarized_segments'] = diarized_segments
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logging.error(f"Diarization failed for GUID {guid}: {str(e)}")
            return False