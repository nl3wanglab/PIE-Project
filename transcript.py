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
from pathlib import Path

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
            feature_extractor=feature_extractor,
            chunk_length_s=30,
            return_timestamps=True,
            framework="pt"
        )

        # Initialize Diarization pipeline
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            cache_dir=self.model_dir,
            use_auth_token=self.auth_token,
        )

    def start_transcription(self, video_path: str, guid: str) -> None:
        """Start the transcription process for a video file"""
        try:
            logging.info(f"Initializing transcription for GUID: {guid}")
            
            # Create initial transcription result
            self.transcriptions[guid] = TranscriptionResult(
                video_name=guid,
                status=TranscriptionStatus.PENDING
            )

            # Start transcription in a separate thread
            thread = threading.Thread(
                target=self._process_transcription,
                args=(video_path, guid),
                name=f"transcription-{guid}"
            )
            thread.daemon = True
            thread.start()
            
            logging.info(f"Transcription thread started for GUID: {guid}")
            
        except Exception as e:
            logging.error(f"Error starting transcription: {e}")
            raise

    def _process_transcription(self, video_path: str, guid: str):
        """Process the transcription in a background thread"""
        print(f"\nStarting transcription for GUID: {guid}")
        
        try:
            self.transcriptions[guid].status = TranscriptionStatus.PROCESSING
            
            # Convert video to audio if needed
            audio_path = self._ensure_audio_file(video_path, guid)
            
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
            transcribed_segments = []
            
            for i in range(num_chunks):
                progress = (i + 1) / num_chunks * 100
                print(f"Transcription progress: {progress:.1f}%")
                
                start_sample = i * chunk_duration * sample_rate
                end_sample = min((i + 1) * chunk_duration * sample_rate, audio.shape[1])
                audio_chunk = audio[:, start_sample:end_sample].squeeze().numpy()
                
                # Get transcription with timestamps
                try:
                    result = self.transcription_pipeline(
                        audio_chunk,
                        return_timestamps=True,
                        generate_kwargs={"language": "en"}
                    )
                    
                    # Handle chunks and timestamps safely
                    chunk_start_time = start_sample / sample_rate
                    
                    # Ensure we have chunks in the result
                    if 'chunks' in result:
                        for chunk in result['chunks']:
                            # Validate timestamp format
                            if isinstance(chunk.get('timestamp'), (list, tuple)) and len(chunk['timestamp']) == 2:
                                start_time, end_time = chunk['timestamp']
                                
                                # Handle None or invalid timestamps
                                if start_time is not None and end_time is not None:
                                    segment = {
                                        'text': chunk['text'],
                                        'timestamp': [
                                            chunk_start_time + float(start_time),
                                            chunk_start_time + float(end_time)
                                        ]
                                    }
                                    transcribed_segments.append(segment)
                                else:
                                    # If timestamps are invalid, estimate them based on chunk position
                                    segment = {
                                        'text': chunk['text'],
                                        'timestamp': [
                                            chunk_start_time,
                                            chunk_start_time + (end_sample - start_sample) / sample_rate
                                        ]
                                    }
                                    transcribed_segments.append(segment)
                    else:
                        # If no chunks with timestamps, create a single segment for this chunk
                        segment = {
                            'text': result.get('text', ''),
                            'timestamp': [
                                chunk_start_time,
                                chunk_start_time + (end_sample - start_sample) / sample_rate
                            ]
                        }
                        transcribed_segments.append(segment)

                except Exception as chunk_error:
                    logging.error(f"Error processing chunk {i}: {str(chunk_error)}")
                    # Continue with next chunk instead of failing completely
                    continue

            # Create full transcript with timestamps
            full_transcript = {
                'text': ' '.join(segment['text'] for segment in transcribed_segments),
                'segments': transcribed_segments
            }

            # Save to file
            transcript_dir = os.path.join(os.path.dirname(video_path), 'transcripts')
            os.makedirs(transcript_dir, exist_ok=True)
            
            transcript_path = os.path.join(transcript_dir, f"{guid}_transcript.json")
            
            transcript_data = {
                'guid': guid,
                'full_transcript': full_transcript['text'],
                'segments': full_transcript['segments'],
                'timestamp': str(datetime.datetime.now()),
                'status': TranscriptionStatus.COMPLETED.value
            }
            
            print(f"Saving transcript to: {transcript_path}")
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)

            # Update transcription result
            self.transcriptions[guid].status = TranscriptionStatus.COMPLETED
            self.transcriptions[guid].full_transcript = full_transcript['text']
            self.transcriptions[guid].segments = full_transcript['segments']
            print(f"\nTranscription completed and saved for GUID: {guid}")

        except Exception as e:
            error_msg = f"Transcription failed for GUID {guid}: {str(e)}"
            print(f"\nError: {error_msg}")
            logging.error(error_msg)
            self.transcriptions[guid].status = TranscriptionStatus.FAILED
            self.transcriptions[guid].error = str(e)

    def _ensure_audio_file(self, video_path: str, guid: str) -> str:
        """Convert video to audio if needed"""
        try:
            import moviepy.editor as mp
            
            # Generate output path using GUID
            audio_path = os.path.join(os.path.dirname(video_path), f"{guid}.wav")
            
            # Convert only if audio file doesn't exist
            if not os.path.exists(audio_path):
                logging.info(f"Converting video to audio for GUID: {guid}")
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