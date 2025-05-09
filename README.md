# Diarization Scoring System

A comprehensive video analysis and scoring system that provides detailed metrics for communication analysis, including speaker diarization, heart rate analysis, and various performance metrics.

## Features

- **Video Processing**
  - Support for multiple video formats (MP4, AVI, MOV, MKV, WMV)
  - Automatic noise reduction for improved audio quality
  - Chunked file upload support for large files

- **Transcription & Diarization**
  - Multiple model size options (tiny, base, small, medium, large)
  - Speaker diarization with customizable speaker assignments
  - Real-time transcription status updates

- **Heart Rate Analysis**
  - CSV-based heart rate data import
  - Support for parent/child heart rate tracking
  - Heart rate variability and spike analysis

- **Performance Metrics**
  - Core Performance Metrics:
    - Turn Balance
    - Engagement
    - Clarity
  - Detailed Analysis:
    - Heart Rate Analysis
    - Voice Analysis
    - Silence Analysis

- **User Interface**
  - Modern, responsive web interface
  - Real-time metric updates
  - Interactive scoring system
  - Detailed analytics visualization

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd DiarizationScoring
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python main.py
```

2. Open your web browser and navigate to the local server (typically http://localhost:8000)

3. Upload a video file:
   - Click the upload button
   - Select your video file
   - Choose transcription model size
   - Enable/disable diarization as needed

4. Upload heart rate data (optional):
   - Prepare a CSV file with parent/child heart rate data
   - Upload through the HR data section

5. View and analyze results:
   - Check transcription and diarization results
   - Review performance metrics
   - Analyze detailed metrics
   - Add notes and observations

## File Structure

```
DiarizationScoring/
├── static/
│   ├── uploaded_videos/
│   │   ├── diarization/
│   │   ├── hr_data/
│   │   ├── scores/
│   │   └── transcripts/
│   ├── css/
│   ├── js/
│   └── index.html
├── main.py
├── scoring.py
├── transcript.py
├── requirements.txt
└── README.md
```

## Data Requirements

### Video Files
- Supported formats: MP4, AVI, MOV, MKV, WMV
- Recommended: Clear audio quality for better transcription

### Heart Rate Data
- Format: CSV file
- Required columns:
  - parent: Parent's heart rate in BPM
  - child: Child's heart rate in BPM
- Optional: Timestamp column for synchronization

### Transcription
- Model sizes available:
  - tiny: Fastest, lowest accuracy
  - base: Good balance of speed and accuracy
  - small: Better accuracy, slower
  - medium: High accuracy, slower
  - large: Highest accuracy, slowest

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Specify your license here]

## Support

For support, please [specify contact information or support channels]
