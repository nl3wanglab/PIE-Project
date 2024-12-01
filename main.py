import os
import webview
import base64
import logging
import json
from transcript import TranscriptionManager
import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

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

            # Decode the base64 file data
            file_data = base64.b64decode(file_data.split(',')[1])
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Write the file chunk
            mode = 'wb' if is_first_chunk else 'ab'
            with open(file_path, mode) as f:
                f.write(file_data)
            
            logging.info(f"Chunk written to {file_path}")
            # Return path relative to static folder
            return {"success": True, "path": os.path.join('uploaded_videos', filename)}
        except Exception as e:
            logging.error(f"Error saving video chunk {filename}: {e}")
            return {"success": False, "error": str(e)}

    def upload_video_chunk(self, file_data, filename, is_first_chunk, total_size):
        try:
            result = self._handle_upload(file_data, filename, is_first_chunk)
            
            # Calculate total file size and current size to determine if this is the last chunk
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            current_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            if result["success"]:
                # Check if this is the last chunk (no more data coming)
                is_last_chunk = current_size >= int(total_size)
                
                if is_last_chunk:  # Only start transcription after full upload
                    print(f"\n=== Starting transcription process for {filename} ===")
                    logging.info(f"Starting transcription for {filename}")
                    video_path = os.path.join(UPLOAD_FOLDER, filename)  # Define video_path here
                    self.transcription_manager.start_transcription(video_path)
                    logging.info(f"Transcription started for {filename}")
                    print(f"=== Transcription process initiated for {filename} ===\n")
                    result["transcriptionStatus"] = "processing"
                    
            return result
        except Exception as e:
            print(f"\n!!! Error in upload_video_chunk: {e} !!!\n")
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

def main():
    # Create a webview window
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700, js_api=API())
    webview.start(debug=True)

if __name__ == "__main__":
    main() 