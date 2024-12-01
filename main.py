import os
import webview
import base64
import logging

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
        
    def upload_video_chunk(self, file_data, filename, is_first_chunk):
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

    def test_connection(self):
        logging.info("JavaScript successfully called Python!")
        return "Connection successful"

    def get_pure_transcript(self, video_name):
        try:
            transcript_path = os.path.join("full_transcription.txt")
            if os.path.exists(transcript_path):
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    return {"success": True, "text": f.read()}
            else:
                return {"success": False, "error": "Transcript file not found"}
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

def main():
    # Create a webview window
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700, js_api=API())
    webview.start(debug=True)

if __name__ == "__main__":
    main() 