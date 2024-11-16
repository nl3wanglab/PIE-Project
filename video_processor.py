import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

UPLOAD_FOLDER = os.path.join('static', 'uploaded_videos')
THUMBNAIL_FOLDER = os.path.join('static', 'thumbnails')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

def save_video(file_path, file_data):
    try:
        with open(file_path, 'wb') as f:
            f.write(file_data)
        logging.debug(f"Video saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving video to {file_path}: {e}")
        raise

def process_video(file_data, filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        save_video(file_path, file_data)
        logging.info(f"Video processing complete for {filename}")
        
        # Return paths relative to static folder
        return {
            "video_path": os.path.join('uploaded_videos', filename),
            "thumbnail_path": extract_thumbnail(file_path, filename)
        }
    except Exception as e:
        logging.error(f"Error processing video: {e}")
        return None
