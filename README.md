# Parent-Child Interaction Analysis Tool

A professional tool for analyzing and improving parent-child interactions through video analysis, speech recognition, and physiological response tracking.

## System Overview

This tool provides comprehensive analysis of parent-child interactions by:
1. Transcribing conversations using advanced AI
2. Identifying who is speaking (parent vs. child)
3. Analyzing communication patterns and engagement
4. Tracking physiological responses through heart rate data
5. Generating detailed metrics and insights

## Technical Requirements

### Hardware Requirements
- Computer with Windows, Mac, or Linux
- Minimum 8GB RAM (16GB recommended)
- GPU recommended for faster processing (CUDA or MPS compatible)

### Software Requirements
- Python 3.11.7 (required - other versions may cause compatibility issues)
- Internet connection for initial setup
- Web browser (Chrome, Firefox, or Safari recommended)

## Installation Guide

### Step 1: Prepare Your System
1. Install Python 3.11.7 from [python.org](https://python.org/downloads/release/python-3117/)
   - For Windows: Download and run the Windows installer (64-bit)
   - For Mac: Download and run the macOS installer
   - For Linux: Use your package manager or build from source
2. Ensure pip (Python package manager) is installed
3. Download or clone this repository to your computer

### Step 2: Set Up Python Environment
1. Open a terminal/command prompt
2. Navigate to the project directory
3. Create a virtual environment:
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On Mac/Linux
   python -m venv venv
   source venv/bin/activate
   ```

### Step 3: Install Dependencies
1. With the virtual environment activated, install required packages:
   ```bash
   pip install -r requirements.txt
   ```
2. Wait for all packages to install (this may take several minutes)
3. The installation includes:
   - Web interface components (Flask, pywebview)
   - Audio processing libraries (librosa, soundfile)
   - Machine learning models (Whisper, PyTorch)
   - Data analysis tools (pandas, numpy)

### Step 4: Configure API Access
1. Create a `token.json` file in the project root
2. Add your Hugging Face API token:
   ```json
   {
       "HUGGING_FACE_TOKEN": "your_token_here"
   }
   ```

## Starting the Application

1. Ensure you're in the project directory with the virtual environment activated
2. Run the application:
   ```bash
   python main.py
   ```
3. A window will open automatically with the application interface
4. The application runs locally on your computer - no internet connection needed after initial setup

## Using the Application

### 1. Uploading a Video
- Click "Upload Video" in the interface
- Select your video file (supported formats: MP4, AVI, MOV, MKV, WMV)
- Choose analysis accuracy:
  - Fast: Quick results, lower accuracy
  - Balanced: Good speed and accuracy
  - Accurate: Best results, slower processing

### 2. Processing Your Video
The system will:
1. Convert the video to audio
2. Apply noise reduction
3. Transcribe the conversation
4. Identify speakers (parent vs. child)
5. Generate initial metrics

### 3. Adding Heart Rate Data (Optional)
1. Prepare a CSV file with columns:
   - parent: Parent's heart rate in BPM
   - child: Child's heart rate in BPM
2. Click "Upload Heart Rate Data"
3. Select your CSV file
4. The system will synchronize the data with the video

### 4. Understanding the Results

#### Conversation Analysis
- **Turn Taking**: Shows who spoke when and for how long
- **Balance**: Measures the distribution of speaking time
- **Patterns**: Identifies communication patterns

#### Engagement Metrics
- **Speech Rate**: Measures how quickly each person speaks
- **Participation**: Shows how actively each person engages
- **Response Time**: Analyzes gaps between speakers

#### Communication Clarity
- **Vocabulary Usage**: Analyzes word choice and complexity
- **Sentence Structure**: Evaluates communication clarity
- **Repetition**: Identifies repeated phrases or patterns

#### Heart Rate Analysis (if provided)
- **Speaking HR**: Heart rate while speaking
- **Listening HR**: Heart rate while listening
- **Variability**: Changes in heart rate during interaction
- **Synchronization**: How heart rates respond to each other

### 5. Saving and Exporting
- All data is automatically saved
- Results can be exported for further analysis
- Notes can be added to specific segments

## Troubleshooting

### Common Issues
1. **Application Won't Start**
   - Ensure Python is installed correctly
   - Check if virtual environment is activated
   - Verify all dependencies are installed

2. **Video Processing Errors**
   - Check video format is supported
   - Ensure video has clear audio
   - Try a different analysis accuracy setting

3. **Heart Rate Data Issues**
   - Verify CSV format is correct
   - Check data synchronization
   - Ensure timestamps match video duration

### Getting Help
- Check the debug.log file for detailed error information
- Contact support with specific error messages
- Include system information when reporting issues

## Technical Details

### Core Components
- **main.py**: Application entry point and API server
- **transcript.py**: Handles audio transcription and speaker identification
- **scoring.py**: Calculates interaction metrics and scores
- **prompt_llm.py**: Optional AI analysis of interactions
- **prompt_deepseek.py**: Optional advanced AI analysis

### Data Storage
- Videos and audio files: `static/uploaded_videos/`
- Transcripts: `static/uploaded_videos/transcripts/`
- Heart rate data: `static/uploaded_videos/hr_data/`
- Analysis results: `static/uploaded_videos/scores/`

### Security
- All data is stored locally
- No data is sent to external servers
- API tokens are stored securely

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License
[Specify your license here]

## Support
For support, please [specify contact information or support channels]
