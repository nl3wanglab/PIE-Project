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
- Mac computer
- Minimum 8GB RAM (16GB recommended)
- GPU recommended for faster processing (MPS compatible)

### Software Requirements
- Python 3.11.7 (will be automatically downloaded to the project directory)
- Internet connection for initial setup and Python download
- Web browser (Chrome, Firefox, or Safari recommended)

### Mac-Specific Requirements
- Developer mode enabled in System Settings (for running downloaded applications)

#### Note about Security
When running the setup script, macOS may ask for permission to download files. This is normal and safe.

## Installation Guide

### Quick Setup Option (Recommended)
If you already have Python 3.8+ installed on your system, you can use the quick setup script:

1. **Make the setup script executable:**
   ```bash
   chmod +x setup_venv.sh
   ```

2. **Run the quick setup:**
   ```bash
   ./setup_venv.sh
   ```
   
   **What this script does:**
   - ✅ Checks your Python version
   - ✅ Creates a virtual environment using your system Python
   - ✅ Installs all dependencies from requirements.txt
   - ✅ Provides activation instructions

3. **After setup, always activate before use:**
   ```bash
   source venv/bin/activate
   ```

### Full Setup Option (If you need Python 3.11.7)
If you don't have Python or need the specific version, use the comprehensive setup:

### Step 1: Prepare Your System
1. Download or clone this repository to your computer
2. Open Terminal
3. Navigate to the project directory:
   ```bash
   cd /path/to/DiarizationScoring
   ```

### Step 2: Set Up Python Environment with Automatic Version Download

**Important:** This step will download a portable Python 3.11.7 build to the project directory and create a virtual environment that uses only this version.

1. **Make the setup script executable:**
   ```bash
   chmod +x setup_python.sh
   ```

2. **Run the setup script:**
   ```bash
   ./setup_python.sh
   ```
   
   **What this script does:**
   - ✅ Checks if Python 3.11.7 is already set up locally
   - ✅ Downloads a portable Python 3.11.7 build from python-build-standalone (≈16 MB)
   - ✅ Extracts Python 3.11.7 to the project directory (`python-3.11.7/`)
   - ✅ Creates a virtual environment using this Python version
   - ✅ Provides clear next steps

3. **No administrator privileges required!** 
   - The script downloads and extracts files only to the project directory
   - No system-wide installation or modifications

4. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

5. **Verify the correct Python version:**
   ```bash
   python --version
   # Should output: Python 3.11.7
   ```

**Troubleshooting:**
- If the script fails to download, check your internet connection
- If extraction fails, ensure you have write permissions in the project directory
- If you get security warnings, go to System Settings > Privacy & Security and allow the downloaded file
- The script can be run multiple times safely - it will skip steps that are already complete

### Step 3: Install Dependencies (if using manual setup)
If you used `setup_python.sh`, dependencies are already installed. Otherwise:

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

## Virtual Environment Management

### Important Notes
- **Always activate the virtual environment** before running the application or installing packages
- The `venv/` folder contains all Python dependencies and should **never be committed to git**
- If you see import errors, make sure your virtual environment is activated

### Daily Usage
1. **Open Terminal and navigate to project:**
   ```bash
   cd /path/to/DiarizationScoring
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```
   
   You should see `(venv)` at the beginning of your command prompt when activated.

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **Deactivate when done (optional):**
   ```bash
   deactivate
   ```

### Managing Dependencies
- **Add new packages:** With venv activated: `pip install package_name`
- **Update requirements:** After adding packages: `pip freeze > requirements.txt`
- **Reinstall all dependencies:** `pip install -r requirements.txt`

### Troubleshooting Virtual Environment
- **If activation fails:** Re-run the setup script (`./setup_venv.sh` or `./setup_python.sh`)
- **If packages are missing:** Activate venv and run `pip install -r requirements.txt`
- **If venv is corrupted:** Delete the `venv/` folder and re-run setup script

## Using the Application

### 1. Uploading a Video
- Click "Upload Video" in the interface
- Select your video file (supported formats: MP4, AVI, MOV, MKV, WMV)
- Choose analysis accuracy:
  - Fast (tiny model):
    - Model size: 39M parameters
    - Fastest processing time
    - Basic transcription accuracy
    - Best for quick initial analysis
    - Suitable for clear audio with minimal background noise
  
  - Balanced (base model):
    - Model size: 74M parameters
    - Moderate processing time
    - Good transcription accuracy
    - Best for most use cases
    - Handles moderate background noise well
  
  - Accurate (small model):
    - Model size: 244M parameters
    - Longer processing time
    - High transcription accuracy
    - Good for detailed analysis
    - Handles complex audio well
  
  - High Accuracy (medium model):
    - Model size: 769M parameters
    - Extended processing time
    - Very high transcription accuracy
    - Best for research or detailed analysis
    - Excellent at handling complex audio with background noise
  
  - Maximum Accuracy (large model):
    - Model size: 1.5B parameters
    - Longest processing time
    - Highest transcription accuracy
    - Best for critical analysis
    - Superior at handling challenging audio conditions
    - Recommended for final analysis or important recordings

Note: Processing time will vary based on video length and your computer's specifications. Larger models require more RAM and GPU memory.

### 2. Processing Your Video
The system will:
1. Convert the video to audio
2. Apply noise reduction
3. Transcribe the conversation
4. Identify speakers (parent vs. child)
5. Generate initial metrics

### 3. Adding Heart Rate Data (Optional)
1. Prepare a CSV file with the following format:
   ```csv
   parent,child
   75,82
   76,83
   77,82
   78,81
   ```
   Required columns:
   - `parent`: Parent's heart rate in BPM (beats per minute)
   - `child`: Child's heart rate in BPM (beats per minute)

   Note: Each row represents a 1-second interval. The system will automatically assign timestamps based on the order of the data points.

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

### Version Control & Environment
- **Virtual environments** (`venv/`, `env/`, etc.) are automatically excluded from git
- **Cache files** (`__pycache__/`, `*.pyc`) are ignored
- **User data** (`static/uploaded_videos/`) is excluded from version control
- **API tokens** (`token.json`) are kept private
- The `.gitignore` file ensures only source code is tracked

### Security
- All data is stored locally
- No data is sent to external servers
- API tokens are stored securely

## Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request