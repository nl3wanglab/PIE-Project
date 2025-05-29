# DiarizationScoring: Parent-Child Interaction Analysis Tool

A comprehensive, research-grade tool for analyzing parent-child interactions through advanced video transcription, speaker identification, emotion analysis, and physiological response tracking. Built for researchers, clinicians, and anyone studying human interaction patterns.

## 📖 Table of Contents

- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Installation](#-installation)
- [Quick Start Guide](#-quick-start-guide)
- [Complete Usage Guide](#-complete-usage-guide)
- [Analysis Features](#-analysis-features)
- [Data Formats](#-data-formats)
- [API Reference](#-api-reference)
- [File Structure](#-file-structure)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Performance Optimization](#-performance-optimization)
- [Security & Privacy](#-security--privacy)
- [Acknowledgments](#-acknowledgments)

## ✨ Features

### Core Analysis Capabilities
- **🎥 Video Transcription**: State-of-the-art Whisper AI with 5 accuracy levels (39M-1.5B parameters)
- **👥 Speaker Diarization**: Advanced automatic identification with manual editing capabilities
- **😊 Emotion Analysis**: Real-time sentiment tracking with chronological visualization
- **❤️ Heart Rate Integration**: Physiological response correlation and analysis
- **📊 Interaction Metrics**: Comprehensive communication pattern analysis
- **🔄 Real-time Processing**: Live analysis with progress tracking

### User Interface & Experience
- **🌐 Web-based Interface**: Modern, responsive design with video playback
- **✏️ Interactive Editing**: Click-to-edit speaker assignments, keyboard shortcuts
- **📈 Visual Analytics**: Real-time charts, emotion indicators, engagement metrics
- **💾 Auto-save**: Continuous backup of all edits and annotations
- **📁 Data Management**: Organized file storage with export capabilities

### Research & Clinical Features
- **📝 Note-taking**: Integrated annotation system for observations
- **🔍 Detailed Metrics**: Turn balance, speech rates, silence analysis

## 💻 System Requirements

### Minimum Requirements
- **Operating System**: macOS 10.14+ (Mojave or later)
- **Processor**: Intel Core i5 or Apple M1/M2
- **Memory**: 8GB RAM (16GB strongly recommended)
- **Storage**: 2GB free space (more for video storage)
- **Python**: **3.8 to 3.11** (3.10-3.11 recommended)

### Recommended Configuration
- **Processor**: Intel Core i7/i9 or Apple M1 Pro/Max/Ultra
- **Memory**: 16GB+ RAM
- **Storage**: SSD with 10GB+ free space
- **GPU**: Optional (for faster processing)

### Python Version Compatibility

| Version | Status | Notes |
|---------|--------|-------|
| 3.8.x | ✅ Supported | Minimum required |
| 3.9.x | ✅ Supported | Good compatibility |
| 3.10.x | ✅ Recommended | Excellent compatibility |
| 3.11.x | ✅ **Best** | Optimal performance |
| 3.12.x | ⚠️ Limited | PyTorch compatibility issues |
| 3.13.x+ | ❌ Not Supported | Requires newer PyTorch |

> ⚠️ **Important**: Python 3.12+ has known compatibility issues with PyTorch dependencies. We strongly recommend Python 3.10 or 3.11.

## 🚀 Installation

### Step 1: Compatibility Check
First, verify your system compatibility:
```bash
python3 check_compatibility.py
```

### Step 2: Choose Installation Method

#### Option A: Automatic Setup (Recommended)
For new installations or if you need Python 3.11.7:
```bash
chmod +x setup_python.sh
./setup_python.sh
```

#### Option B: Use Existing Python
If you already have Python 3.8-3.11:
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

### Step 3: Activate Environment
```bash
source venv/bin/activate
```

### Step 4: Verify Installation
```bash
python check_compatibility.py
python main.py
```

## 🎯 Quick Start Guide

### 1. Launch Application
```bash
cd /path/to/DiarizationScoring
source venv/bin/activate
python main.py
```

### 2. Upload Your First Video
1. Click **"Upload Video"** in the web interface
2. Select a video file (MP4, AVI, MOV, MKV, WMV)
3. Choose analysis accuracy:
   - **Tiny**: Fastest (39M parameters)
   - **Base**: Good balance (74M parameters)
   - **Small**: Better accuracy (244M parameters)
   - **Medium**: High accuracy (769M parameters)
   - **Large**: Best accuracy (1.5B parameters)

### 3. Review Transcription
- View automatic transcript with timestamps
- Check speaker identification (Parent/Child)
- Edit speaker assignments if needed

### 4. Analyze Results
- Review emotion indicators
- Check interaction metrics
- Add notes and observations

## 📚 Complete Usage Guide

### Video Upload & Processing

#### Supported Formats
- **Video**: MP4, AVI, MOV, MKV, WMV
- **Audio**: Extracted automatically
- **Maximum Size**: Limited by available disk space
- **Recommended**: 1080p or lower for faster processing

#### Processing Pipeline
1. **Video Upload**: Chunked upload for large files
2. **Audio Extraction**: Conversion to WAV format
3. **Noise Reduction**: Optional preprocessing
4. **Transcription**: Whisper AI processing
5. **Speaker Diarization**: Automatic speaker identification
6. **Emotion Analysis**: Sentiment extraction
7. **Metrics Calculation**: Interaction scoring

### Speaker Management

#### Automatic Diarization
- Uses advanced machine learning models
- Identifies speaker changes automatically
- Labels speakers as "Parent" and "Child"

#### Manual Editing
- **Click to Select**: Click transcript segments to select
- **Keyboard Shortcuts**:
  - `P`: Assign to Parent
  - `C`: Assign to Child
  - `Ctrl/Cmd + Click`: Multi-select
- **Swap Button**: Instantly swap all speaker assignments
- **Save Changes**: Automatic saving of edits

### Emotion Analysis

#### Supported Emotions
- **Joy**: Happiness, excitement, contentment
- **Sadness**: Disappointment, grief, melancholy
- **Anger**: Frustration, irritation, rage
- **Fear**: Anxiety, worry, apprehension
- **Surprise**: Astonishment, wonder, amazement
- **Love**: Affection, caring, tenderness

#### Visualization
- **Timeline View**: Emotions displayed chronologically
- **Color-coded Badges**: Visual emotion indicators
- **Confidence Scores**: Analysis certainty levels
- **Speaker Summaries**: Emotion breakdowns by person

### Heart Rate Integration

#### Data Requirements
- **Format**: CSV file with time-series data
- **Columns**: `parent,child` (BPM values)
- **Frequency**: 1-second intervals recommended
- **Synchronization**: Manual time alignment

#### Example Format
```csv
parent,child
72,85
73,86
74,84
75,87
```

#### Analysis Features
- **HR Variability**: Statistical analysis of heart rate changes
- **Correlation**: Relationship between HR and interaction events
- **Visualization**: Real-time charts and trends
- **Export**: Data export for further analysis

## 🔬 Analysis Features

### Transcription Accuracy Levels

| Model | Parameters | Speed | Accuracy | Use Case |
|-------|------------|-------|----------|----------|
| Tiny | 39M | Fastest | Good | Quick previews |
| Base | 74M | Fast | Better | General use |
| Small | 244M | Medium | High | Research |
| Medium | 769M | Slow | Very High | Publication quality |
| Large | 1.5B | Slowest | Best | Critical analysis |

### Interaction Metrics

#### Communication Patterns
- **Turn Balance**: Speaking time distribution
- **Turn Duration**: Average length of speaking turns
- **Response Time**: Delay between speakers
- **Interruptions**: Overlap detection and analysis
- **Participation Rate**: Overall engagement levels

#### Audio Features
- **Pitch Analysis**: Fundamental frequency patterns
- **Speech Rate**: Words per minute calculation
- **Silence Detection**: Pause analysis
- **Volume Levels**: Amplitude variation
- **Voice Quality**: Spectral analysis

#### Emotional Metrics
- **Emotional Arc**: Sentiment progression over time
- **Emotional Contagion**: Speaker influence patterns
- **Mood Stability**: Emotional consistency
- **Dominant Emotions**: Primary emotional states
- **Transition Patterns**: Emotional flow analysis

## 📄 Data Formats

### Input Formats

#### Video Files
```
Supported: .mp4, .avi, .mov, .mkv, .wmv
Recommended: MP4 with H.264 encoding
Audio: Any format (automatically extracted)
```

#### Heart Rate Data
```csv
# Required columns: parent, child
# Optional: timestamp (if not sequential)
parent,child,timestamp
75,82,0
76,83,1
77,82,2
```

### Output Formats

#### Transcript Files
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "speaker": "PARENT",
      "text": "How was your day at school?",
      "confidence": 0.95
    }
  ],
  "metadata": {
    "duration": 120.5,
    "model": "base",
    "language": "en"
  }
}
```

#### Score Files
```json
{
  "basic_metrics": {
    "total_duration": 120.5,
    "parent_speaking_time": 65.2,
    "child_speaking_time": 55.3
  },
  "detailed_metrics": {
    "turn_balance": 0.85,
    "average_turn_duration": 3.2,
    "sentiment_analysis": {
      "chronological_emotions": [...]
    }
  }
}
```

## 🔧 API Reference

### Main Application (main.py)

#### Core Methods
```python
class VideoAnalysisAPI:
    def upload_video(self, file_data, filename)
    def start_transcription(self, guid, model_size)
    def get_transcription_status(self, guid)
    def save_diarization(self, guid, segments)
    def calculate_scores(self, guid, config)
    def save_notes(self, guid, notes)
```

### Transcription Engine (transcript.py)

#### TranscriptionManager
```python
class TranscriptionManager:
    def transcribe_audio(self, audio_path, model_size)
    def perform_diarization(self, audio_path)
    def get_status(self, guid)
    def cancel_transcription(self, guid)
```

### Scoring System (scoring.py)

#### ScoringSystem
```python
class ScoringSystem:
    def calculate_basic_scores(self, transcript_data)
    def calculate_audio_features(self, audio_path)
    def calculate_sentiment_analysis(self, segments)
    def calculate_heart_rate_metrics(self, hr_data)
```

## 📁 File Structure

```
DiarizationScoring/
├── 📄 main.py                      # Application entry point & API
├── 📄 transcript.py                # Audio processing & diarization
├── 📄 scoring.py                   # Metrics calculation engine
├── 📄 prompt_llm.py                # Local LLM integration
├── 📄 prompt_deepseek.py           # DeepSeek API integration
├── 📄 video_processor.py           # Video utilities
├── 📄 check_compatibility.py       # System compatibility checker
├── 📄 requirements.txt             # Python dependencies
├── 📄 setup_venv.sh               # Environment setup script
├── 📄 setup_python.sh             # Python installation script
├── 📄 README.md                   # This documentation
├── 📄 COMPATIBILITY_CHANGES.md    # Compatibility information
├── 📁 static/                     # Web interface & data storage
│   ├── 📄 index.html              # Main interface
│   ├── 📄 video-viewer.html       # Analysis interface
│   ├── 📄 viewer.js               # JavaScript functionality
│   ├── 📁 uploaded_videos/        # User data storage
│   │   ├── 📁 transcripts/        # Transcript JSON files
│   │   ├── 📁 scores/             # Analysis results
│   │   ├── 📁 notes/              # User annotations
│   │   └── 📁 thumbnails/         # Video thumbnails
│   └── 📁 css/                    # Stylesheets
└── 📁 venv/                       # Virtual environment (auto-created)
```

### Data Storage Organization

```
static/uploaded_videos/
├── {video_guid}.mp4               # Original video
├── {video_guid}.wav               # Extracted audio
├── {video_guid}_hr.csv            # Heart rate data
├── {video_guid}_notes.txt         # User notes
├── transcripts/
│   ├── {video_guid}_transcript.json
│   └── {video_guid}_diarization.json
├── scores/
│   └── {video_guid}_scores.json
└── thumbnails/
    └── {video_guid}_thumb.jpg
```

## ⚙️ Configuration

### Environment Configuration

#### Token Setup (Optional)
For advanced AI analysis, create `token.json`:
```json
{
    "HUGGING_FACE_TOKEN": "hf_your_token_here",
    "DEEPSEEK_API_KEY": "your_deepseek_key_here"
}
```

#### Application Settings
Edit configuration in `main.py`:
```python
# Server configuration
HOST = "127.0.0.1"
PORT = 5000
DEBUG = False

# Processing configuration
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
NOISE_REDUCTION = True
AUTO_DIARIZATION = True

# Model preferences
DEFAULT_MODEL = "base"
ENABLE_GPU = True
```

### Advanced Configuration

#### Whisper Model Configuration
```python
# In transcript.py
WHISPER_MODELS = {
    "tiny": {"size": "tiny", "memory": "1GB"},
    "base": {"size": "base", "memory": "1GB"},
    "small": {"size": "small", "memory": "2GB"},
    "medium": {"size": "medium", "memory": "5GB"},
    "large": {"size": "large", "memory": "10GB"}
}
```

#### Scoring Configuration
```python
# In scoring.py
SCORING_CONFIG = {
    "turn_balance_weight": 0.3,
    "response_time_weight": 0.2,
    "emotion_weight": 0.3,
    "participation_weight": 0.2
}
```

## 🔧 Troubleshooting

### Common Issues & Solutions

#### Python Version Issues
```bash
# Problem: Python 3.12+ compatibility errors
# Solution: Install Python 3.11.7
./setup_python.sh

# Problem: Multiple Python versions
# Solution: Specify version explicitly
python3.11 -m venv venv
```

#### Installation Problems
```bash
# Problem: Permission denied
# Solution: Fix script permissions
chmod +x setup_venv.sh setup_python.sh

# Problem: Pip installation fails
# Solution: Upgrade pip and try again
pip install --upgrade pip
pip install -r requirements.txt
```

#### Processing Errors
```bash
# Problem: Out of memory during transcription
# Solution: Use smaller model or increase swap
# Use "tiny" or "base" model instead of "large"

# Problem: Audio extraction fails
# Solution: Check video format and codec
ffmpeg -i input.mp4 -ar 16000 output.wav
```

#### Performance Issues
```bash
# Problem: Slow processing
# Solutions:
# 1. Use smaller Whisper model
# 2. Reduce video resolution
# 3. Enable noise reduction: False
# 4. Close other applications
```

### Debug Mode

Enable debug logging:
```python
# In main.py
import logging
logging.basicConfig(level=logging.DEBUG)

# View logs
tail -f debug.log
```

### System Diagnostics

Run comprehensive system check:
```bash
python check_compatibility.py
```

Check specific components:
```bash
# Test video processing
python -c "import moviepy; print('MoviePy OK')"

# Test audio processing
python -c "import librosa; print('Librosa OK')"

# Test ML components
python -c "import torch; print(f'PyTorch {torch.__version__}')"
```

## ⚡ Performance Optimization

### Hardware Optimization

#### Memory Management
- **16GB RAM**: Recommended for large model processing
- **SSD Storage**: Significantly faster than HDD
- **Multiple Cores**: Parallel processing benefits

#### GPU Acceleration (Optional)
```python
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Enable GPU processing
ENABLE_GPU = True  # in main.py
```

### Software Optimization

#### Model Selection Strategy
- **Development**: Use "tiny" or "base" models
- **Testing**: Use "small" model
- **Production**: Use "medium" or "large" models
- **Research**: Use "large" model only

#### Processing Optimization
```python
# Optimize for speed
NOISE_REDUCTION = False      # Disable for faster processing
CHUNK_SIZE = 1024 * 1024    # Larger chunks for faster upload
BATCH_PROCESSING = True      # Process multiple files together
```

#### File Management
- **Regular Cleanup**: Remove old processed files
- **Compression**: Use compressed video formats
- **Batch Processing**: Process multiple videos together

## 🔒 Security & Privacy

### Data Privacy

#### Local Processing
- **No Cloud Upload**: All processing happens locally
- **No Data Transmission**: No data sent to external servers
- **Local Storage**: All files remain on your computer
- **Secure Deletion**: Proper file cleanup when requested

#### Optional External Services
- **Hugging Face**: Only if token provided
- **DeepSeek API**: Only if enabled and token provided
- **User Control**: All external services are opt-in

### File Security

#### Data Encryption
- **At Rest**: Files stored unencrypted (local machine)
- **In Transit**: HTTPS for external API calls
- **Temporary Files**: Securely cleaned up

#### Access Control
- **Local Only**: Web interface bound to localhost
- **No Remote Access**: Not accessible from network
- **User Permissions**: Standard file system permissions

### Best Practices

#### Token Management
```bash
# Store tokens securely
chmod 600 token.json

# Never commit tokens to version control
echo "token.json" >> .gitignore
```

#### Data Management
```bash
# Regular cleanup of sensitive data
rm -rf static/uploaded_videos/old_data/

# Backup important results
cp -r static/uploaded_videos/ backup/
```

## 👥 Contributing

### Development Setup

1. **Fork & Clone**
```bash
git clone https://github.com/yourusername/DiarizationScoring.git
cd DiarizationScoring
```

2. **Development Environment**
```bash
./setup_venv.sh
source venv/bin/activate
pip install -e .
```

3. **Install Development Dependencies**
```bash
pip install -r requirements.txt[dev]
```

### Code Standards

#### Python Style
- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations
- **Docstrings**: Document all functions
- **Testing**: Write unit tests for new features

#### Frontend Standards
- **ES6+**: Modern JavaScript syntax
- **Responsive Design**: Mobile-friendly interface
- **Accessibility**: WCAG 2.1 compliance
- **Performance**: Optimize for speed

### Testing

#### Unit Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_transcription.py

# Coverage report
python -m pytest --cov=. tests/
```

#### Integration Tests
```bash
# Test full pipeline
python -m pytest tests/test_integration.py

# Test with sample data
python tests/test_with_sample_video.py
```

### Submitting Changes

1. **Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make Changes & Test**
```bash
# Make your changes
git add .
git commit -m "Add your feature description"

# Test thoroughly
python -m pytest
python check_compatibility.py
```

3. **Submit Pull Request**
- Clear description of changes
- Reference any related issues
- Include test results
- Update documentation if needed

## Acknowledgments

### Technology Stack
- **[OpenAI Whisper](https://github.com/openai/whisper)**: State-of-the-art speech recognition
- **[pyannote.audio](https://github.com/pyannote/pyannote-audio)**: Speaker diarization
- **[Transformers](https://github.com/huggingface/transformers)**: NLP and emotion analysis
- **[Flask](https://flask.palletsprojects.com/)**: Web framework
- **[PyWebView](https://pywebview.flowrl.com/)**: Desktop application framework

---

### Getting Help
- **Documentation**: This README covers most use cases
- **Compatibility Issues**: Run `python check_compatibility.py`
- **GitHub Issues**: Report bugs and request features

### Reporting Issues
When reporting issues, please include:
- Python version (`python --version`)
- Operating system and version
- Error messages (full traceback)
- Steps to reproduce
- Sample data (if applicable and privacy-safe)


Built for researchers, clinicians, and anyone interested in understanding human interaction patterns.