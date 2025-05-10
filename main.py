import os
import webview
import base64
import logging
import json
from transcript import TranscriptionManager, TranscriptionStatus
import datetime
import sys
import uuid
import noisereduce as nr
import soundfile as sf
import numpy as np
from pydub import AudioSegment
import pandas as pd
import csv
from scoring import ScoringSystem

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Add this line to see all debug messages
logging.getLogger().setLevel(logging.DEBUG)

# Also add some initial logging to verify it's working
logging.info("=== Application Starting ===")
logging.info(f"Current working directory: {os.getcwd()}")

UPLOAD_FOLDER = os.path.join('static', 'uploaded_videos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class API:
    def __init__(self):
        self.upload_folder = os.path.join('static', 'uploaded_videos')
        # Initialize without default model - will be set on first use
        self.transcription_manager = TranscriptionManager()
        self.scoring_system = ScoringSystem()
        
    def _save_filename_mapping(self, guid, original_filename):
        """Save mapping between GUID and original filename"""
        mapping_file = os.path.join(UPLOAD_FOLDER, 'filename_mapping.json')
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
            else:
                mapping = {}
            
            mapping[guid] = {
                'original_filename': original_filename,
                'timestamp': str(datetime.datetime.now())
            }
            
            with open(mapping_file, 'w') as f:
                json.dump(mapping, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving filename mapping: {e}")

    def get_original_filename(self, guid):
        """Get original filename from GUID"""
        mapping_file = os.path.join(UPLOAD_FOLDER, 'filename_mapping.json')
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
                    return mapping.get(guid, {}).get('original_filename')
        except Exception as e:
            logging.error(f"Error getting original filename: {e}")
        return None

    def _reduce_noise(self, audio_path):
        """Apply noise reduction to audio file"""
        try:
            logging.info(f"Applying noise reduction to {audio_path}")
            
            # Convert video to wav if needed
            if not audio_path.endswith('.wav'):
                audio = AudioSegment.from_file(audio_path)
                wav_path = os.path.splitext(audio_path)[0] + '.wav'
                audio.export(wav_path, format='wav')
            else:
                wav_path = audio_path

            # Load audio file
            data, rate = sf.read(wav_path)
            
            # Convert to mono if stereo
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Apply noise reduction
            reduced_noise = nr.reduce_noise(
                y=data,
                sr=rate,
                prop_decrease=0.75,
                stationary=True
            )

            # Save processed audio
            processed_path = os.path.splitext(audio_path)[0] + '_processed.wav'
            sf.write(processed_path, reduced_noise, rate)
            
            logging.info(f"Noise reduction complete. Saved to {processed_path}")
            return processed_path

        except Exception as e:
            logging.error(f"Error during noise reduction: {e}")
            return audio_path  # Return original path if processing fails

    def upload_video(self, file_data, filename, use_diarization=False, model_size="base"):
        """Handle video upload and start transcription"""
        try:
            logging.info(f"Processing video upload: {filename} (diarization: {use_diarization}, model: {model_size})")
            
            # Validate model size
            valid_models = ["tiny", "base", "small", "medium", "large"]
            if model_size not in valid_models:
                logging.warning(f"Invalid model size {model_size}, falling back to base")
                model_size = "base"
                
            # Check file extension
            allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
            file_extension = os.path.splitext(filename)[1].lower()
            
            if file_extension not in allowed_extensions:
                error_msg = (
                    f"File '{filename}' is not supported.\n"
                    f"Only video files are allowed.\n"
                    f"Supported formats: {', '.join(allowed_extensions)}"
                )
                logging.warning(f"Invalid file upload attempt: {error_msg}")
                return {"success": False, "error": error_msg}

            # Generate GUID
            file_guid = str(uuid.uuid4())
            guid_filename = f"{file_guid}{file_extension}"
            file_path = os.path.join(UPLOAD_FOLDER, guid_filename)

            try:
                # Decode the base64 file data
                file_data = base64.b64decode(file_data.split(',')[1])
            except Exception as e:
                logging.error(f"Error decoding base64 data: {e}")
                return {"success": False, "error": "Invalid file data"}

            # Write the file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            logging.info(f"File written to {file_path}")
            
            # Store filename mapping
            self._save_filename_mapping(file_guid, filename)
            
            # Start transcription with specified model
            self.transcription_manager.start_transcription(
                file_path, 
                file_guid, 
                use_diarization,
                model_size=model_size
            )

            return {
                "success": True,
                "path": os.path.join('uploaded_videos', guid_filename),
                "guid": file_guid,
                "original_filename": filename,
                "transcriptionStatus": "processing",
                "model": model_size
            }

        except Exception as e:
            logging.error(f"Error in upload_video: {str(e)}")
            return {"success": False, "error": str(e)}

    def upload_video_chunk(self, file_data, filename, is_first_chunk, total_size, use_diarization=False, model_size="base"):
        """Handle video upload and start transcription"""
        try:
            logging.info(f"Processing video upload: {filename} (diarization: {use_diarization}, model: {model_size})")
            
            # Validate model size
            valid_models = ["tiny", "base", "small", "medium", "large"]
            if model_size not in valid_models:
                logging.warning(f"Invalid model size {model_size}, falling back to base")
                model_size = "base"
            
            # Check file extension
            allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
            file_extension = os.path.splitext(filename)[1].lower()
            
            if file_extension not in allowed_extensions:
                error_msg = (
                    f"File '{filename}' is not supported.\n"
                    f"Only video files are allowed.\n"
                    f"Supported formats: {', '.join(allowed_extensions)}"
                )
                logging.warning(f"Invalid file upload attempt: {error_msg}")
                return {"success": False, "error": error_msg}

            # Generate GUID for first chunk only
            if is_first_chunk:
                file_guid = str(uuid.uuid4())
                self._save_filename_mapping(file_guid, filename)
            else:
                file_guid = os.path.splitext(filename)[0]

            guid_filename = f"{file_guid}{file_extension}"
            file_path = os.path.join(UPLOAD_FOLDER, guid_filename)

            try:
                # Decode the base64 file data
                file_data = base64.b64decode(file_data.split(',')[1])
            except Exception as e:
                logging.error(f"Error decoding base64 data: {e}")
                return {"success": False, "error": "Invalid file data"}

            # Write the file
            mode = 'wb' if is_first_chunk else 'ab'
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, mode) as f:
                f.write(file_data)
            
            logging.info(f"File data written to {file_path}")

            # Only start transcription when file is complete
            current_size = os.path.getsize(file_path)
            if current_size >= total_size:
                # Apply noise reduction before transcription
                processed_path = self._reduce_noise(file_path)
                
                # Start transcription with processed file and specified model
                self.transcription_manager.start_transcription(
                    processed_path, 
                    file_guid, 
                    use_diarization,
                    model_size=model_size
                )
                return {
                    "success": True,
                    "path": os.path.join('uploaded_videos', guid_filename),
                    "guid": file_guid,
                    "original_filename": filename,
                    "transcriptionStatus": "processing",
                    "model": model_size
                }

            # Still receiving file data
            return {
                "success": True,
                "path": os.path.join('uploaded_videos', guid_filename),
                "guid": file_guid,
                "original_filename": filename,
                "transcriptionStatus": "uploading"
            }

        except Exception as e:
            logging.error(f"Error in upload_video_chunk: {str(e)}")
            return {"success": False, "error": str(e)}

    def test_connection(self):
        logging.info("JavaScript successfully called Python!")
        return "Connection successful"

    def get_pure_transcript(self, video_name):
        try:
            # Look for transcript in the transcripts directory
            transcript_path = os.path.join(UPLOAD_FOLDER, 'transcripts', f"{video_name}_transcript.json")
            
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    return {
                        "success": True, 
                        "text": transcript_data['full_transcript'],
                        "timestamp": transcript_data['timestamp']
                    }
            else:
                # Try getting from transcription manager if file not found
                result = self.transcription_manager.get_transcription_status(video_name)
                if result and result.full_transcript:
                    return {
                        "success": True,
                        "text": result.full_transcript,
                        "timestamp": str(datetime.datetime.now())
                    }
                return {"success": False, "error": "Transcript not found"}
        except Exception as e:
            logging.error(f"Error reading pure transcript: {e}")
            return {"success": False, "error": str(e)}
    
    def get_diarized_transcript(self, video_name):
        try:
            transcript_path = os.path.join("diarization_transcript.txt")
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    # Parse the diarization transcript into segments
                    segments = []
                    current_segment = None
                    
                    for line in f:
                        line = line.strip()
                        if line:
                            if ' - ' in line and ': Speaker' in line:
                                # New time segment
                                if current_segment:
                                    segments.append(current_segment)
                                
                                # Parse the timestamp line
                                parts = line.split(': Speaker ')
                                time_range = parts[0]
                                speaker = parts[1]
                                
                                current_segment = {
                                    "start": time_range.split(' - ')[0],
                                    "end": time_range.split(' - ')[1],
                                    "speaker": speaker,
                                    "text": ""
                                }
                            elif line.startswith('Transcription:'):
                                if current_segment:
                                    current_segment["text"] = line.split(':', 1)[1].strip()
                
                    if current_segment:
                        segments.append(current_segment)
                
                    return {"success": True, "segments": segments}
            else:
                return {"success": False, "error": "Diarized transcript file not found"}
        except Exception as e:
            logging.error(f"Error reading diarized transcript: {e}")
            return {"success": False, "error": str(e)}

    def delete_video(self, guid):
        """Delete video and associated files by GUID"""
        try:
            # Find the file extension from the mapping
            mapping_file = os.path.join(UPLOAD_FOLDER, 'filename_mapping.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
                
                if guid in mapping:
                    # Get original filename to determine extension
                    original_filename = mapping[guid]['original_filename']
                    extension = os.path.splitext(original_filename)[1]
                    
                    # Delete video file
                    video_path = os.path.join(UPLOAD_FOLDER, f"{guid}{extension}")
                    if os.path.exists(video_path):
                        os.remove(video_path)
                    
                    # Delete transcript file if it exists
                    transcript_path = os.path.join(UPLOAD_FOLDER, "transcripts", f"{guid}_transcript.json")
                    if os.path.exists(transcript_path):
                        os.remove(transcript_path)
                    
                    # Remove from mapping
                    del mapping[guid]
                    with open(mapping_file, 'w') as f:
                        json.dump(mapping, f, indent=2)
                    
                    logging.info(f"Successfully deleted video and associated files for GUID: {guid}")
                    return {"success": True}
                else:
                    logging.warning(f"GUID not found in mapping: {guid}")
                    return {"success": False, "error": "Video not found"}
            else:
                logging.error("Filename mapping file not found")
                return {"success": False, "error": "Mapping file not found"}
            
        except Exception as e:
            logging.error(f"Error deleting video {guid}: {e}")
            return {"success": False, "error": str(e)}

    def get_transcription_status(self, video_name):
        """Get the current status of video transcription"""
        try:
            result = self.transcription_manager.get_transcription_status(video_name)
            if result:
                return {
                    "success": True,
                    "status": result.status.value,
                    "full_transcript": result.full_transcript,
                    "diarized_segments": result.diarized_segments,
                    "error": result.error
                }
            return {"success": False, "error": "Transcription not found"}
        except Exception as e:
            logging.error(f"Error getting transcription status: {e}")
            return {"success": False, "error": str(e)}

    def view_transcript(self, video_name):
        """API endpoint to get transcript data"""
        try:
            print("\n=== View Transcript Request ===")
            print(f"Video name: {video_name}")
            print(f"Current working directory: {os.getcwd()}")
            
            logging.info(f"=== View Transcript Request ===")
            logging.info(f"Video name: {video_name}")
            logging.info(f"Current working directory: {os.getcwd()}")
            
            # First try getting from the transcription manager
            print("Attempting to get transcript from TranscriptionManager...")
            logging.info("Attempting to get transcript from TranscriptionManager...")
            result = self.transcription_manager.get_transcript(video_name)
            
            if result:
                logging.info(f"Found transcript for {video_name}")
                return {"success": True, "data": result}
            else:
                logging.warning("No transcript found in file system")
            
            # If not found, check if it's still processing
            logging.info("Checking transcription status...")
            status = self.transcription_manager.get_transcription_status(video_name)
            if status:
                logging.info(f"Status found: {status.status.value}")
                if status.status == TranscriptionStatus.PROCESSING:
                    return {"success": False, "error": "Transcript is still processing"}
                elif status.status == TranscriptionStatus.FAILED:
                    return {"success": False, "error": f"Transcription failed: {status.error}"}
                elif status.status == TranscriptionStatus.PENDING:
                    return {"success": False, "error": "Transcription is pending"}
            else:
                logging.warning("No transcription status found")
            
            logging.warning(f"No transcript or status found for {video_name}")
            return {"success": False, "error": "Transcript not found"}
            
        except Exception as e:
            logging.error(f"Error viewing transcript: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_transcript(self, guid):
        """Get transcript for a video using GUID"""
        try:
            print(f"\n=== Getting Transcript for GUID: {guid} ===")
            
            # Look for transcript in the uploaded_videos/transcripts directory
            transcript_path = os.path.join(UPLOAD_FOLDER, "transcripts", f"{guid}_transcript.json")
            print(f"Looking for transcript at: {transcript_path}")
            
            if os.path.exists(transcript_path):
                print(f"Found transcript file at {transcript_path}")
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                return {"success": True, "data": transcript_data}
            
            # If not found in file, check transcription manager
            print("Checking transcription manager...")
            status = self.transcription_manager.get_transcription_status(guid)
            if status:
                if status.status == TranscriptionStatus.COMPLETED and status.full_transcript:
                    return {
                        "success": True,
                        "data": {
                            "video_name": guid,
                            "full_transcript": status.full_transcript,
                            "timestamp": str(datetime.datetime.now()),
                            "status": status.status.value
                        }
                    }
                elif status.status == TranscriptionStatus.PROCESSING:
                    return {"success": False, "error": "Transcript is still processing"}
                elif status.status == TranscriptionStatus.FAILED:
                    return {"success": False, "error": f"Transcription failed: {status.error}"}
            
            print(f"No transcript found for GUID: {guid}")
            return {"success": False, "error": "Transcript not found"}
            
        except Exception as e:
            print(f"Error getting transcript: {str(e)}")
            logging.error(f"Error getting transcript: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_all_mapped_files(self):
        """Get all mapped files from the filename mapping"""
        try:
            mapping_file = os.path.join(UPLOAD_FOLDER, 'filename_mapping.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
                return {"success": True, "files": mapping}
            return {"success": True, "files": {}}
        except Exception as e:
            logging.error(f"Error getting mapped files: {e}")
            return {"success": False, "error": str(e)}

    def upload_hr_data(self, file_data, guid):
        """Handle HR data file upload"""
        try:
            logging.info(f"Processing HR data upload for GUID: {guid}")
            
            # Create HR data directory if it doesn't exist
            hr_data_dir = os.path.join(UPLOAD_FOLDER, 'hr_data')
            os.makedirs(hr_data_dir, exist_ok=True)
            
            # Save the HR data file
            hr_file_path = os.path.join(hr_data_dir, f"{guid}_hr.csv")
            
            try:
                # Parse the CSV data directly
                lines = file_data.split('\n')
                if len(lines) < 2:  # Need at least header and one data row
                    return {"success": False, "error": "CSV file must contain data rows"}
                
                # Create DataFrame from the processed data
                df = pd.DataFrame([line.split(',') for line in lines[1:]], columns=['parent', 'child'])
                
                # Convert to numeric, replacing any invalid values with NaN
                df['parent'] = pd.to_numeric(df['parent'], errors='coerce')
                df['child'] = pd.to_numeric(df['child'], errors='coerce')
                
                # Remove any rows with NaN values
                df = df.dropna()
                
                if df.empty:
                    return {"success": False, "error": "No valid numeric data found in CSV"}
                
                # Save the processed data
                df.to_csv(hr_file_path, index=False)
                
                logging.info(f"HR data saved to {hr_file_path}")
                return {"success": True, "message": "HR data uploaded successfully"}
                
            except Exception as e:
                logging.error(f"Error processing HR data: {e}")
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            logging.error(f"Error in upload_hr_data: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_hr_data(self, guid):
        """Get HR data for a video using GUID"""
        try:
            hr_file_path = os.path.join(UPLOAD_FOLDER, 'hr_data', f"{guid}_hr.csv")
            if os.path.exists(hr_file_path):
                df = pd.read_csv(hr_file_path)
                data = df.to_dict('records')
                return {"success": True, "data": data}
            return {"success": False, "error": "HR data not found"}
        except Exception as e:
            logging.error(f"Error getting HR data: {str(e)}")
            return {"success": False, "error": str(e)}

    def save_scores(self, guid, scores_from_payload):
        logging.info(f"Attempting to save scores for GUID: {guid}")
        try:
            scores_dir = os.path.join(UPLOAD_FOLDER, 'scores')
            os.makedirs(scores_dir, exist_ok=True)
            scores_file = os.path.join(scores_dir, f"{guid}_scores.json")

            existing_scores = {}
            if os.path.exists(scores_file):
                try:
                    with open(scores_file, 'r') as f:
                        existing_scores = json.load(f)
                    logging.info(f"Loaded existing scores for GUID {guid} from {scores_file}")
                except json.JSONDecodeError:
                    logging.error(f"Could not decode existing scores file for GUID {guid}. Will overwrite.", exc_info=True)
                    existing_scores = {} # Start fresh if file is corrupt
            
            # Ensure base structure in existing_scores for merging
            if 'scores' not in existing_scores or not isinstance(existing_scores['scores'], dict):
                existing_scores['scores'] = {}
            if 'detailed_metrics' not in existing_scores or not isinstance(existing_scores['detailed_metrics'], dict):
                existing_scores['detailed_metrics'] = {}

            # Update main scores
            if 'scores' in scores_from_payload and isinstance(scores_from_payload['scores'], dict):
                for metric_key, new_data_for_metric in scores_from_payload['scores'].items():
                    logging.debug(f"Processing main score for metric '{metric_key}'. New data: {new_data_for_metric}")
                    if not isinstance(new_data_for_metric, dict):
                        logging.warning(f"Malformed new_data for main score '{metric_key}'. Expected dict, got {type(new_data_for_metric)}. Skipping.")
                        continue

                    if metric_key not in existing_scores['scores']:
                        existing_scores['scores'][metric_key] = {} # Initialize if new metric

                    # Preserve 'original' from existing file if it exists and is valid, otherwise take from new_data
                    if 'original' in existing_scores['scores'][metric_key]:
                        logging.debug(f"Main metric '{metric_key}': Kept existing 'original' value: {existing_scores['scores'][metric_key]['original']}")
                    elif 'original' in new_data_for_metric:
                        existing_scores['scores'][metric_key]['original'] = new_data_for_metric['original']
                        logging.debug(f"Main metric '{metric_key}': Set 'original' from new data: {new_data_for_metric['original']}")
                    else:
                        # Fallback for 'original' if completely missing
                        fallback_original = new_data_for_metric.get('current', 0)
                        existing_scores['scores'][metric_key]['original'] = fallback_original
                        logging.warning(f"Main metric '{metric_key}': Missing 'original' in new data. Set 'original' to current value: {fallback_original}")
                    
                    # Update 'current', 'label', 'description'
                    existing_scores['scores'][metric_key]['current'] = new_data_for_metric.get('current', existing_scores['scores'][metric_key].get('original', 0)) # Fallback to original if current missing
                    if 'label' in new_data_for_metric:
                        existing_scores['scores'][metric_key]['label'] = new_data_for_metric['label']
                    if 'description' in new_data_for_metric:
                        existing_scores['scores'][metric_key]['description'] = new_data_for_metric['description']

            # Update detailed metrics (similar logic)
            if 'detailed_metrics' in scores_from_payload and isinstance(scores_from_payload['detailed_metrics'], dict):
                for metric_key, new_data_for_metric in scores_from_payload['detailed_metrics'].items():
                    logging.debug(f"Processing detailed metric '{metric_key}'. New data (first 200 chars): {str(new_data_for_metric)[:200]}")
                    if not isinstance(new_data_for_metric, dict):
                        logging.warning(f"Malformed new_data for detailed_metric '{metric_key}'. Expected dict, got {type(new_data_for_metric)}. Skipping.")
                        continue

                    if metric_key not in existing_scores['detailed_metrics']:
                        existing_scores['detailed_metrics'][metric_key] = {}

                    if 'original' in existing_scores['detailed_metrics'][metric_key]:
                        logging.debug(f"Detailed metric '{metric_key}': Kept existing 'original' value.")
                    elif 'original' in new_data_for_metric:
                        existing_scores['detailed_metrics'][metric_key]['original'] = new_data_for_metric['original']
                        logging.debug(f"Detailed metric '{metric_key}': Set 'original' from new data.")
                    else:
                        fallback_original = new_data_for_metric.get('current', {})
                        existing_scores['detailed_metrics'][metric_key]['original'] = fallback_original
                        logging.warning(f"Detailed metric '{metric_key}': Missing 'original' in new data. Set 'original' to current value.")

                    existing_scores['detailed_metrics'][metric_key]['current'] = new_data_for_metric.get('current', existing_scores['detailed_metrics'][metric_key].get('original', {}))
                    if 'label' in new_data_for_metric:
                        existing_scores['detailed_metrics'][metric_key]['label'] = new_data_for_metric['label']
                    if 'description' in new_data_for_metric:
                        existing_scores['detailed_metrics'][metric_key]['description'] = new_data_for_metric['description']
            
            existing_scores['timestamp'] = scores_from_payload.get('timestamp', str(datetime.datetime.now()))
            
            with open(scores_file, 'w') as f:
                json.dump(existing_scores, f, indent=2)
            
            logging.info(f"Successfully saved scores for GUID {guid} to {scores_file}. Final structure keys: scores={list(existing_scores['scores'].keys())}, detailed_metrics={list(existing_scores['detailed_metrics'].keys())}")
            return {"success": True}

        except KeyError as ke:
            logging.error(f"KeyError while saving scores for GUID {guid}: '{ke}' was missing. Scores data being processed (first 500 chars): {str(scores_from_payload)[:500]}", exc_info=True)
            return {"success": False, "error": f"Missing key during score saving: {ke}"}
        except Exception as e:
            logging.error(f"Unexpected error saving scores for GUID {guid}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_scores(self, guid):
        """Get scoring data for a video"""
        try:
            scores_file = os.path.join(UPLOAD_FOLDER, 'scores', f"{guid}_scores.json")
            if os.path.exists(scores_file):
                with open(scores_file, 'r') as f:
                    data = json.load(f)
                    return {"success": True, "data": data}
            return {"success": True, "data": {
                'scores': {},
                'detailed_metrics': {},
                'timestamp': str(datetime.datetime.now())
            }}
        except Exception as e:
            logging.error(f"Error getting scores: {e}")
            return None

    def calculate_scores(self, guid):
        logging.info(f"Received request to calculate scores for GUID: {guid}")
        try:
            # 1. Determine the actual audio file path
            original_filename = self.get_original_filename(guid)
            if not original_filename:
                logging.error(f"Could not find original filename for GUID: {guid}")
                return {"success": False, "error": "Original filename not found for GUID."}
            
            file_extension = os.path.splitext(original_filename)[1]
            # Try both processed and original audio paths
            processed_audio_filename = f"{guid}_processed.wav"
            original_audio_filename = f"{guid}{file_extension}"
            
            actual_audio_file_path = None
            potential_paths = [
                os.path.join(self.upload_folder, processed_audio_filename),
                os.path.join(self.upload_folder, original_audio_filename)
            ]

            for path_option in potential_paths:
                if os.path.exists(path_option):
                    actual_audio_file_path = path_option
                    logging.info(f"Using audio file for scoring: {actual_audio_file_path}")
                    break
            
            if not actual_audio_file_path:
                logging.error(f"No audio file found for GUID: {guid} (checked {potential_paths})")
                return {"success": False, "error": f"Audio file not found for GUID {guid}."}

            # 2. Load full transcript data
            transcript_file_path = os.path.join(UPLOAD_FOLDER, "transcripts", f"{guid}_transcript.json")
            full_transcript_data = None
            if os.path.exists(transcript_file_path):
                try:
                    with open(transcript_file_path, 'r') as f:
                        full_transcript_data = json.load(f)
                    logging.info(f"Loaded full transcript data from: {transcript_file_path}")
                except Exception as e:
                    logging.error(f"Error loading full transcript data for {guid}: {e}")
                    # Continue without it, scoring.py should handle None
            else:
                logging.warning(f"Full transcript file not found: {transcript_file_path}")

            # 3. Load dedicated diarization data (if it exists)
            diarization_file_path = os.path.join(UPLOAD_FOLDER, "transcripts", f"{guid}_diarization.json")
            diarization_file_content = None
            if os.path.exists(diarization_file_path):
                try:
                    with open(diarization_file_path, 'r') as f:
                        diarization_file_content = json.load(f)
                    logging.info(f"Loaded dedicated diarization data from: {diarization_file_path}")
                except Exception as e:
                    logging.error(f"Error loading dedicated diarization data for {guid}: {e}")
                    # Continue without it, scoring.py uses transcript's diarized_segments as fallback
            else:
                logging.info(f"Dedicated diarization file not found (this is okay, will use transcript fallback): {diarization_file_path}")

            # 4. Load HR data (if it exists)
            hr_file_path = os.path.join(UPLOAD_FOLDER, "hr_data", f"{guid}_hr_data.csv")
            hr_file_content = None
            if os.path.exists(hr_file_path):
                try:
                    hr_df = pd.read_csv(hr_file_path)
                    hr_file_content = hr_df.to_dict(orient='records')
                    logging.info(f"Loaded HR data from: {hr_file_path}")
                except Exception as e:
                    logging.error(f"Error loading HR data for {guid}: {e}")
                    # Continue without it, scoring.py should handle None
            else:
                logging.info(f"HR data file not found: {hr_file_path}")

            # 5. Call ScoringSystem
            logging.info(f"Calling scoring_system.calculate_all_scores with audio_path: {actual_audio_file_path}, full_transcript_data: {'present' if full_transcript_data else 'absent'}, diarization_data_content: {'present' if diarization_file_content else 'absent'}, hr_data: {'present' if hr_file_content else 'absent'}")
            scores_result = self.scoring_system.calculate_all_scores(
                audio_file_path=actual_audio_file_path,
                full_transcript_data=full_transcript_data,
                diarization_data_content=diarization_file_content,
                hr_data=hr_file_content
            )

            if scores_result and scores_result.get('success', False):
                # Save the detailed metrics and scores (calculate_all_scores now returns a dict with 'success' and 'data')
                self.save_scores(guid, scores_result['data']) # Corrected back to save_scores
                logging.info(f"Scores calculated and saved successfully for GUID: {guid}. Result (first 200 chars of data): {str(scores_result['data'])[:200]}")
                return scores_result # Return the full result including success status and data
            else:
                error_message = scores_result.get('error', 'Unknown error during score calculation') if scores_result else 'Score calculation returned None'
                logging.error(f"Score calculation failed for GUID {guid}: {error_message}")
                return {"success": False, "error": error_message}

        except Exception as e:
            logging.error(f"Unexpected error in calculate_scores for GUID {guid}: {e}", exc_info=True)
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def delete_hr_data(self, guid):
        """Delete HR data for a video using GUID"""
        try:
            hr_file_path = os.path.join(UPLOAD_FOLDER, 'hr_data', f"{guid}_hr.csv")
            if os.path.exists(hr_file_path):
                os.remove(hr_file_path)
                logging.info(f"Deleted HR data file: {hr_file_path}")
                return {"success": True, "message": "HR data deleted successfully"}
            return {"success": False, "error": "HR data not found"}
        except Exception as e:
            logging.error(f"Error deleting HR data: {str(e)}")
            return {"success": False, "error": str(e)}

    def log_js_error(self, error_message):
        """Log JavaScript errors from the frontend"""
        logging.error(f"JavaScript Error: {error_message}")
        return {"success": True}

    def save_diarization(self, guid, segments):
        """Save speaker assignments for a video"""
        try:
            # Create diarization directory if it doesn't exist
            diarization_dir = os.path.join(UPLOAD_FOLDER, 'diarization')
            os.makedirs(diarization_dir, exist_ok=True)
            
            # Save to diarization file
            diarization_path = os.path.join(diarization_dir, f"{guid}_diarization.json")
            with open(diarization_path, 'w') as f:
                json.dump({"segments": segments}, f)
            
            # Update the transcript file with new speaker assignments
            transcript_path = os.path.join(UPLOAD_FOLDER, 'transcripts', f"{guid}_transcript.json")
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r') as f:
                    transcript_data = json.load(f)
                
                # Update speaker assignments in diarized segments
                if 'diarized_segments' in transcript_data:
                    for segment in transcript_data['diarized_segments']:
                        # Find matching segment from saved diarization
                        matching_segment = next((s for s in segments if 
                            abs(s['start'] - segment['start']) < 0.1 and 
                            abs(s['end'] - segment['end']) < 0.1), None)
                        if matching_segment:
                            segment['speaker'] = matching_segment['speaker']
                
                # Save updated transcript
                with open(transcript_path, 'w') as f:
                    json.dump(transcript_data, f)
            
            return {"success": True}
        except Exception as e:
            print(f"Error saving diarization: {e}")
            return {"success": False, "error": str(e)}

    def save_notes(self, guid, notes):
        """Save notes for a video"""
        try:
            notes_dir = os.path.join(UPLOAD_FOLDER, 'notes')
            os.makedirs(notes_dir, exist_ok=True)
            
            notes_file = os.path.join(notes_dir, f"{guid}_notes.txt")
            with open(notes_file, 'w') as f:
                f.write(notes)
            
            logging.info(f"Saved notes for {guid}")
            return {"success": True}
        except Exception as e:
            logging.error(f"Error saving notes: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_notes(self, guid):
        """Get notes for a video"""
        try:
            notes_file = os.path.join(UPLOAD_FOLDER, 'notes', f"{guid}_notes.txt")
            if os.path.exists(notes_file):
                with open(notes_file, 'r') as f:
                    notes = f.read()
                    return {"success": True, "data": notes}
            return {"success": True, "data": ""}
        except Exception as e:
            logging.error(f"Error getting notes: {str(e)}")
            return {"success": False, "error": str(e)}

def main():
    # Create a webview window without specifying a backend
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700, js_api=API())
    webview.start(debug=True)  # Enable debug mode

if __name__ == "__main__":
    main() 