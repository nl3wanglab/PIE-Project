import os
import webview
import base64
import logging
import json
from transcript import TranscriptionManager, TranscriptionStatus
import datetime
import sys
import uuid

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler(sys.stdout)
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
        self.transcription_manager = TranscriptionManager()
        
    def _handle_upload(self, file_data, filename, is_first_chunk):
        """Handle the upload of a video chunk"""
        try:
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

            # Generate or retrieve GUID
            if is_first_chunk:
                file_guid = str(uuid.uuid4())
            else:
                # For subsequent chunks, extract GUID from the filename
                file_guid = os.path.splitext(filename)[0]  # Assuming filename is the GUID for subsequent chunks
                
            if not file_guid:
                return {"success": False, "error": "Invalid file identifier"}

            # Create the full path with GUID
            guid_filename = f"{file_guid}{file_extension}"
            file_path = os.path.join(UPLOAD_FOLDER, guid_filename)
            
            # Decode the base64 file data
            try:
                file_data = base64.b64decode(file_data.split(',')[1])
            except Exception as e:
                logging.error(f"Error decoding base64 data: {e}")
                return {"success": False, "error": "Invalid file data"}

            # Write the file chunk
            mode = 'wb' if is_first_chunk else 'ab'
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, mode) as f:
                f.write(file_data)
            
            logging.info(f"Chunk written to {file_path}")
            
            # Store filename mapping if this is the first chunk
            if is_first_chunk:
                self._save_filename_mapping(file_guid, filename)
            
            return {
                "success": True, 
                "path": os.path.join('uploaded_videos', guid_filename),
                "guid": file_guid,
                "original_filename": filename
            }
        except Exception as e:
            logging.error(f"Error saving video chunk {filename}: {e}")
            return {"success": False, "error": str(e)}

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

    def upload_video_chunk(self, file_data, filename, is_first_chunk, total_size):
        """Handle video chunk upload and start transcription when complete"""
        try:
            logging.info(f"Processing chunk upload: {filename} (first_chunk: {is_first_chunk}, total_size: {total_size})")
            
            result = self._handle_upload(file_data, filename, is_first_chunk)
            
            if result["success"]:
                file_guid = result["guid"]
                file_extension = os.path.splitext(filename)[1]
                file_path = os.path.join(UPLOAD_FOLDER, f"{file_guid}{file_extension}")
                
                try:
                    current_size = os.path.getsize(file_path)
                    upload_progress = (current_size / total_size) * 100
                    result["uploadProgress"] = upload_progress
                    
                    logging.info(f"Upload progress for {file_guid}: {upload_progress:.1f}%")
                    
                    # Check if upload is complete
                    if current_size >= total_size:
                        logging.info(f"Upload complete for {file_guid}, starting transcription")
                        self.transcription_manager.start_transcription(file_path, file_guid)
                        result["transcriptionStatus"] = "processing"
                    else:
                        logging.info(f"Waiting for more chunks... ({current_size}/{total_size} bytes)")
                        result["transcriptionStatus"] = "uploading"
                except Exception as e:
                    logging.error(f"Error checking file size: {e}")
                    return {"success": False, "error": str(e)}
                
            return result
        except Exception as e:
            logging.error(f"Error in upload_video_chunk: {e}")
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

    def delete_video(self, filename):
        try:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Successfully deleted video: {filename}")
                return {"success": True}
            else:
                logging.warning(f"File not found for deletion: {filename}")
                return {"success": False, "error": "File not found"}
        except Exception as e:
            logging.error(f"Error deleting video {filename}: {e}")
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

    def _validate_upload_completion(self, file_path, total_size):
        """Validate that the upload is complete and file is valid"""
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist"
            
            current_size = os.path.getsize(file_path)
            if current_size < total_size:
                return False, f"Incomplete upload ({current_size}/{total_size} bytes)"
            
            # Basic file integrity check
            try:
                with open(file_path, 'rb') as f:
                    # Read first few bytes to verify file is accessible
                    f.read(1024)
                return True, None
            except Exception as e:
                return False, f"File integrity check failed: {str(e)}"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

def main():
    # Create a webview window
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700, js_api=API())
    webview.start(debug=True)

if __name__ == "__main__":
    main() 