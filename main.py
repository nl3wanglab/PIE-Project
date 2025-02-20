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
        # Initialize with default model
        self.transcription_manager = TranscriptionManager(model_size="base")
        
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
            
            # Start transcription immediately with specified model
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

def main():
    # Create a webview window without specifying a backend
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700, js_api=API())
    webview.start(debug=True)  # Enable debug mode

if __name__ == "__main__":
    main() 