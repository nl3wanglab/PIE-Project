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
    def upload_video_chunk(self, file_data, filename, is_first_chunk):
        try:
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

def main():
    # Create a webview window
    window = webview.create_window('Video Dashboard', 'static/index.html', width=1000, height=700, js_api=API())
    webview.start(debug=True)

if __name__ == "__main__":
    main() 