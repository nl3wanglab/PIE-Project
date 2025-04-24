#!/usr/bin/env python
import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import time
from tqdm import tqdm
import torch
import warnings
import json

# Suppress unnecessary warnings
warnings.filterwarnings("ignore")

def check_and_install_packages():
    """Check for required packages and install if missing"""
    required_packages = {
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'tqdm': 'tqdm',
        'torch': 'torch',
        'pyannote.audio': 'pyannote.audio',
        'moviepy': 'moviepy',
        'pydub': 'pydub',
        'scipy': 'scipy',
        'ffmpeg': 'ffmpeg-python',  # Changed key to avoid confusion
    }
    
    missing_packages = []
    for package, pip_name in required_packages.items():
        try:
            if package == 'pyannote.audio':
                # Special case for pyannote.audio which has a dot in the name
                try:
                    __import__('pyannote.audio')
                    print(f"Package {package} is already installed.")
                except ImportError:
                    missing_packages.append(pip_name)
            elif package == 'ffmpeg':
                # Special case for ffmpeg-python
                try:
                    import ffmpeg
                    print(f"Package {package} is already installed.")
                except ImportError:
                    missing_packages.append(pip_name)
            else:
                __import__(package)
                print(f"Package {package} is already installed.")
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("Missing required packages. Installing now...")
        import subprocess
        
        for package in missing_packages:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
                if package == 'pyannote.audio':
                    print("For pyannote.audio, trying alternative installation method...")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                                              "pyannote.audio", "-f", 
                                              "https://github.com/pyannote/pyannote-audio/releases"])
                        print("Successfully installed pyannote.audio")
                    except subprocess.CalledProcessError as e:
                        print(f"Failed alternative installation: {e}")
        
        print("All required packages installed successfully.")
        
        # Only restart if we actually installed something
        if missing_packages:
            print("Restarting script...")
            args = sys.argv.copy()
            os.execv(sys.executable, [sys.executable] + args)
        else:
            print("No new packages were installed, continuing...")

# Check for packages before trying to import them
check_and_install_packages()

# Now import the required packages
from moviepy.editor import VideoFileClip
from pyannote.audio import Pipeline
from pyannote.core import Segment, Timeline, Annotation
import ffmpeg

def extract_audio_from_video(video_path, audio_output_path=None, fallback_method=False):
    """
    Extract audio from video file and save as WAV.
    Uses moviepy by default with ffmpeg as fallback for problematic videos.
    """
    if audio_output_path is None:
        audio_output_path = os.path.splitext(video_path)[0] + ".wav"
    
    # First check if the file exists and is accessible
    if not os.path.exists(video_path):
        print(f"Error: Video file {video_path} does not exist")
        return None
    
    if fallback_method:
        return extract_audio_ffmpeg(video_path, audio_output_path)
    
    try:
        print("Extracting audio from video...")
        
        # Create a simple progress indicator
        sys.stdout.write("Starting audio extraction...\n")
        
        # Load the video file
        video = VideoFileClip(video_path)
        
        if video.audio is None:
            print("No audio track found in the video. Checking with ffmpeg...")
            return extract_audio_ffmpeg(video_path, audio_output_path)
        
        # Use a simple animated progress indicator
        import threading
        import itertools
        
        def animate():
            # Simple spinner animation
            spinner = itertools.cycle(['-', '/', '|', '\\'])
            while not done:
                sys.stdout.write('\rExtracting audio... ' + next(spinner))
                sys.stdout.flush()
                time.sleep(0.1)
            sys.stdout.write('\rExtraction completed!      \n')
        
        # Flag to control the animation
        done = False
        
        # Start the animation in a background thread
        t = threading.Thread(target=animate)
        t.daemon = True
        t.start()
        
        # Extract the audio (this might take a while)
        try:
            video.audio.write_audiofile(audio_output_path, codec='pcm_s16le', logger=None)
        finally:
            # Stop the animation
            done = True
            t.join(timeout=1)
            video.close()
        
        print(f"Audio extracted and saved to {audio_output_path}")
        return audio_output_path
    except Exception as e:
        print(f"Error extracting audio with moviepy: {e}")
        print("Trying alternative extraction method with ffmpeg...")
        return extract_audio_ffmpeg(video_path, audio_output_path)

def extract_audio_ffmpeg(video_path, audio_output_path):
    """Extract audio using direct ffmpeg command for problematic videos."""
    try:
        print("Extracting audio using ffmpeg...")
        
        # Run ffmpeg command to extract audio
        import subprocess
        
        # Create a progress display
        process = subprocess.Popen([
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', '-y', audio_output_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Display progress indicator
        print("Processing with ffmpeg (this may take a while)...")
        
        # Simple spinner animation
        import itertools
        import threading
        import time
        
        done = False
        def animate():
            spinner = itertools.cycle(['-', '/', '|', '\\'])
            while not done:
                sys.stdout.write('\rExtracting audio... ' + next(spinner))
                sys.stdout.flush()
                time.sleep(0.1)
            sys.stdout.write('\rExtraction completed!      \n')
        
        # Start animation
        t = threading.Thread(target=animate)
        t.daemon = True
        t.start()
        
        # Wait for the process to complete
        process.communicate()
        done = True
        t.join(timeout=1)
        
        # Check if the file was created
        if process.returncode != 0:
            print(f"Error: ffmpeg returned code {process.returncode}")
            return None
        
        if os.path.exists(audio_output_path) and os.path.getsize(audio_output_path) > 0:
            print(f"Audio extracted and saved to {audio_output_path}")
            return audio_output_path
        else:
            print(f"Error: Failed to extract audio, output file empty or missing")
            return None
            
    except Exception as e:
        print(f"Error extracting audio with ffmpeg: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_audio_file(audio_path):
    """Validate that the audio file exists and can be processed."""
    if not os.path.exists(audio_path):
        print(f"Error: Audio file {audio_path} does not exist")
        return False
    
    # Check file size is not zero
    if os.path.getsize(audio_path) == 0:
        print(f"Error: Audio file {audio_path} is empty")
        return False
    
    # Try to open the file with pydub to validate format
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000.0
        
        if duration < 0.1:
            print(f"Warning: Audio file {audio_path} is too short ({duration:.2f} seconds)")
            return False
            
        print(f"Audio file validated: {audio_path} ({duration:.2f} seconds)")
        return True
    except Exception as e:
        print(f"Error validating audio file: {e}")
        return False

def get_pyannote_pipeline(device=None, use_auth=True, token_path=None):
    """
    Get the pyannote.audio pipeline for speaker diarization.
    
    Args:
        device: Device to use (cuda or cpu)
        use_auth: Whether to use authentication
        token_path: Path to a file containing the Hugging Face token
    """
    try:
        # Define device (CPU/GPU)
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
        print(f"Using device: {device}")
        
        use_auth_token = None
        
        if use_auth:
            # First try to read from token.json
            token_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
            if os.path.exists(token_json_path):
                try:
                    with open(token_json_path, 'r') as f:
                        token_data = json.load(f)
                        if isinstance(token_data, dict) and 'HUGGING_FACE_TOKEN' in token_data:
                            use_auth_token = token_data['HUGGING_FACE_TOKEN'].strip()
                            print(f"Using Hugging Face token from token.json")
                except Exception as e:
                    print(f"Error reading token.json: {e}")
            
            # If no token from token.json, check environment variable
            if not use_auth_token:
                use_auth_token = os.environ.get("HF_TOKEN", None)
                if use_auth_token:
                    print("Using Hugging Face token from environment variable")
            
            # If still no token, try the provided token path
            if not use_auth_token and token_path and os.path.exists(token_path):
                with open(token_path, 'r') as f:
                    token_data = json.load(f)
                    if isinstance(token_data, dict) and 'HUGGING_FACE_TOKEN' in token_data:
                        use_auth_token = token_data['HUGGING_FACE_TOKEN'].strip()
                        print(f"Using Hugging Face token from {token_path}")
                    else:
                        use_auth_token = f.read().strip()
                        print(f"Using Hugging Face token from {token_path}")
            
            # If still no token, try default token file
            if not use_auth_token:
                default_token_file = os.path.expanduser("~/.cache/huggingface/token")
                if os.path.exists(default_token_file):
                    with open(default_token_file, 'r') as f:
                        use_auth_token = f.read().strip()
                        print("Using Hugging Face token from default location")
            
            # If still no token, prompt the user
            if not use_auth_token:
                print("\n" + "="*80)
                print("Hugging Face authentication token not found.")
                print("To use pyannote.audio models, you need to:")
                print("1. Create an account on https://huggingface.co/")
                print("2. Visit: https://huggingface.co/pyannote/speaker-diarization")
                print("3. Accept the user agreement for this model")
                print("4. Get your token from: https://huggingface.co/settings/tokens")
                print("="*80 + "\n")
                
                use_auth_token = input("Please enter your Hugging Face token: ").strip()
                
                # Save token for future use
                save_token = input("Save this token for future use? (y/n): ").strip().lower()
                if save_token in ('y', 'yes'):
                    token_dir = os.path.dirname(os.path.expanduser("~/.cache/huggingface/token"))
                    os.makedirs(token_dir, exist_ok=True)
                    with open(os.path.expanduser("~/.cache/huggingface/token"), 'w') as f:
                        f.write(use_auth_token)
                    print("Token saved for future use")
        
        if not use_auth_token:
            print("Error: No valid Hugging Face token found")
            return None
        
        # Initialize the pipeline
        print("Loading pretrained model (this may take a moment)...")
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization@2.1",
                use_auth_token=use_auth_token
            )
            
            # Move pipeline to the appropriate device
            pipeline = pipeline.to(torch.device(device))
            
            return pipeline
            
        except Exception as e:
            print(f"Error loading pipeline: {e}")
            if "401 Client Error" in str(e):
                print("\nAuthentication error: Your Hugging Face token is invalid or expired.")
                print("Please get a new token from https://huggingface.co/settings/tokens")
            elif "403 Client Error" in str(e):
                print("\nAccess denied: You need to accept the model license agreement.")
                print("Visit https://huggingface.co/pyannote/speaker-diarization and accept the terms.")
            return None
    
    except Exception as e:
        print(f"Error initializing pyannote pipeline: {e}")
        import traceback
        traceback.print_exc()
        return None

def perform_diarization(audio_path, num_speakers=None, plot=True, min_speakers=None, max_speakers=None, 
                        token_path=None, progress_callback=None):
    """
    Perform speaker diarization using pyannote.audio.
    
    Args:
        audio_path: Path to the audio file
        num_speakers: Number of speakers (if known)
        plot: Whether to plot the results
        min_speakers: Minimum number of speakers to find (if num_speakers not provided)
        max_speakers: Maximum number of speakers to find (if num_speakers not provided)
        token_path: Path to a file containing the Hugging Face token
        progress_callback: Optional callback function for progress updates
        
    Returns:
        List of speaker segments in the format:
        [{"speaker": 0, "start": 0.0, "end": 1.0, "duration": 1.0}, ...]
    """
    try:
        print(f"Loading diarization pipeline...")
        start_time = time.time()
        
        # Validate audio file
        if not check_audio_file(audio_path):
            print("Audio file validation failed. Cannot proceed with diarization.")
            return None
        
        # Get the pyannote pipeline
        pipeline = get_pyannote_pipeline(token_path=token_path)
        if pipeline is None:
            return None
        
        print(f"Pipeline loaded in {time.time() - start_time:.2f} seconds")
        print(f"Processing audio file: {audio_path}")
        
        # Create parameter dictionary
        diarization_params = {}
        
        # If num_speakers is provided, add it to the parameters
        if num_speakers is not None:
            print(f"Using fixed number of speakers: {num_speakers}")
            diarization_params["num_speakers"] = num_speakers
        
        # If min_speakers or max_speakers is provided
        if min_speakers is not None:
            diarization_params["min_speakers"] = min_speakers
        if max_speakers is not None:
            diarization_params["max_speakers"] = max_speakers
            
        # Perform diarization
        print("Starting diarization process...")
        diarization_start = time.time()
        
        # Create progress bar for visualization
        with tqdm(total=100, desc="Diarizing", unit="%") as pbar:
            # We can't directly monitor pyannote's progress, but we can update based on typical stages
            pbar.update(5)  # Starting
            
            # For long files, we might want to provide some feedback during processing
            def update_progress():
                current = 10
                while current < 90:
                    time.sleep(2)  # Check every 2 seconds
                    if progress_callback:
                        progress_callback(current, "Processing...")
                    pbar.update(1)
                    current += 1
                    if time.time() - diarization_start > 600:  # If taking more than 10 minutes
                        break
            
            # Start progress monitoring in a separate thread for long-running processes
            import threading
            progress_thread = threading.Thread(target=update_progress)
            progress_thread.daemon = True
            progress_thread.start()
            
            # Run the pipeline
            try:
                diarization = pipeline(audio_path, **diarization_params)
                pbar.update(95 - pbar.n)  # Update to 95%
            except Exception as e:
                print(f"Error during diarization: {e}")
                if "CUDA out of memory" in str(e):
                    print("\nGPU memory error. Trying again with CPU...")
                    # Fall back to CPU if CUDA out of memory
                    pipeline = pipeline.to(torch.device("cpu"))
                    diarization = pipeline(audio_path, **diarization_params)
                    pbar.update(95 - pbar.n)
                else:
                    raise
        
        processing_time = time.time() - diarization_start
        print(f"Diarization completed in {processing_time:.2f} seconds")
        
        # Get the duration of the audio file
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000.0  # Convert to seconds
        
        # Report real-time factor
        if duration > 0:
            rtf = processing_time / duration
            print(f"Real-time factor: {rtf:.2f}x ({processing_time:.2f}s processing for {duration:.2f}s audio)")
        
        # Convert PyAnnote result to our segment format
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segment = {
                "speaker": int(speaker.replace("SPEAKER_", "")),
                "start": turn.start,
                "end": turn.end,
                "duration": turn.end - turn.start
            }
            segments.append(segment)
        
        # Sort segments by start time
        segments.sort(key=lambda x: x["start"])
        
        # Print diarization results
        print("\nDiarization Results:")
        print("--------------------")
        
        # Calculate statistics
        total_duration = 0
        speaker_durations = {}
        
        for i, segment in enumerate(segments):
            speaker = segment['speaker']
            duration = segment['duration']
            total_duration += duration
            
            if speaker not in speaker_durations:
                speaker_durations[speaker] = 0
            speaker_durations[speaker] += duration
            
            # For long output, limit printing to first 20 and last 5 segments
            if i < 20 or i >= len(segments) - 5 or len(segments) <= 25:
                print(f"Segment {i+1}: Speaker {speaker} - {segment['start']:.2f}s to {segment['end']:.2f}s (Duration: {duration:.2f}s)")
            elif i == 20:
                print(f"... ({len(segments) - 25} more segments) ...")
        
        # Print speaker statistics
        print("\nSpeaker Statistics:")
        print("------------------")
        for speaker, duration in speaker_durations.items():
            percentage = (duration / total_duration) * 100
            print(f"Speaker {speaker}: {duration:.2f}s ({percentage:.2f}%)")
        
        # Plot results if requested
        if plot:
            plot_diarization(segments, len(speaker_durations), duration, audio_path)
        
        # Save results to file
        save_diarization_to_file(segments, audio_path)
        
        return segments
    
    except Exception as e:
        print(f"Error performing diarization: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to create at least some basic output with simple content
        if "segments" in locals() and segments:
            print("Saving partial results despite error...")
            try:
                save_diarization_to_file(segments, audio_path)
                print("Partial results saved.")
                return segments
            except:
                pass
                
        return None

def plot_diarization(segments, num_speakers, duration, audio_path):
    """Plot the diarization results."""
    try:
        print("Generating diarization plot...")
        plt.figure(figsize=(15, 4))
        
        # Create timeline
        timeline = np.linspace(0, duration, int(duration * 10))  # 10 frames per second
        labels = np.zeros(len(timeline))
        
        for segment in segments:
            start_idx = int(segment['start'] * 10)  # 10 frames per second
            end_idx = int(segment['end'] * 10)
            
            # Ensure indices are within bounds
            start_idx = max(0, min(start_idx, len(labels)-1))
            end_idx = max(start_idx, min(end_idx, len(labels)))
            
            labels[start_idx:end_idx] = segment['speaker']
        
        plt.plot(timeline, labels)
        plt.yticks(np.arange(num_speakers), [f"Speaker {i}" for i in range(num_speakers)])
        plt.xlabel("Time (seconds)")
        plt.ylabel("Speaker")
        plt.title(f"Speaker Diarization for {os.path.basename(audio_path)}")
        plt.grid(True)
        
        # Save plot
        plot_path = os.path.splitext(audio_path)[0] + "_pyannote_diarization.png"
        plt.savefig(plot_path)
        print(f"Diarization plot saved to {plot_path}")
        plt.close()  # Close the figure to free memory
        
    except Exception as e:
        print(f"Error plotting diarization results: {e}")
        import traceback
        traceback.print_exc()

def save_diarization_to_file(segments, audio_path):
    """Save diarization results to text and JSON files."""
    base_path = os.path.splitext(audio_path)[0]
    output_txt_path = base_path + "_pyannote_diarization.txt"
    output_json_path = base_path + "_pyannote_diarization.json"
    
    try:
        print("Saving diarization results to files...")
        
        # Save as text file
        with open(output_txt_path, 'w') as file:
            file.write("Speaker Diarization Results (Pyannote.audio)\n")
            file.write("=========================================\n\n")
            file.write(f"File: {audio_path}\n\n")
            file.write("Segments:\n")
            
            # Calculate statistics
            total_duration = 0
            speaker_durations = {}
            
            for i, segment in enumerate(segments):
                speaker = segment['speaker']
                duration = segment['duration']
                total_duration += duration
                
                if speaker not in speaker_durations:
                    speaker_durations[speaker] = 0
                speaker_durations[speaker] += duration
                
                file.write(f"Segment {i+1}: Speaker {speaker} - {segment['start']:.2f}s to {segment['end']:.2f}s (Duration: {duration:.2f}s)\n")
            
            # Write speaker statistics
            file.write("\nSpeaker Statistics:\n")
            file.write("------------------\n")
            for speaker, duration in speaker_durations.items():
                percentage = (duration / total_duration) * 100
                file.write(f"Speaker {speaker}: {duration:.2f}s ({percentage:.2f}%)\n")
        
        # Save as JSON file
        with open(output_json_path, 'w') as json_file:
            json.dump(segments, json_file, indent=2)
        
        print(f"Diarization results saved to {output_txt_path} and {output_json_path}")
        return output_txt_path
    
    except Exception as e:
        print(f"Error saving diarization results: {e}")
        import traceback
        traceback.print_exc()
        return None

def convert_to_rttm(segments, audio_path):
    """Convert diarization results to RTTM format."""
    rttm_path = os.path.splitext(audio_path)[0] + "_pyannote_diarization.rttm"
    file_id = os.path.basename(os.path.splitext(audio_path)[0])
    
    try:
        print("Converting to RTTM format...")
        with open(rttm_path, 'w') as rttm_file:
            for segment in segments:
                # RTTM format: Type File_ID Channel_ID Start_Time Duration Speaker_Type Speaker_ID Confidence Slat
                rttm_file.write(f"SPEAKER {file_id} 1 {segment['start']:.4f} {segment['duration']:.4f} <NA> SPEAKER_{segment['speaker']} <NA> <NA>\n")
        
        print(f"RTTM file saved to {rttm_path}")
        return rttm_path
    
    except Exception as e:
        print(f"Error converting to RTTM format: {e}")
        return None

def preprocess_audio(signal, sampling_rate, fast_mode=True):
    """Apply audio preprocessing to enhance speaker differentiation."""
    print("Applying audio preprocessing to enhance speaker detection...")
    
    try:
        import librosa
        from scipy import signal as sig_proc
        
        # Step 1: Normalize audio
        print("  Normalizing audio levels...")
        normalized_signal = librosa.util.normalize(signal)
        
        # Step 2: Apply noise reduction using spectral gating
        print("  Applying noise reduction...")
        # Compute spectrogram
        D = librosa.stft(normalized_signal, n_fft=2048, hop_length=512)
        # Estimate noise floor from first 2 seconds
        noise_floor = np.mean(np.abs(D[:, :20]), axis=1, keepdims=True)
        # Create noise gate
        noise_gate = 2.0  # Adjust this value to control noise reduction strength
        mask = np.abs(D) > (noise_floor * noise_gate)
        # Apply mask
        D_denoised = D * mask
        # Reconstruct signal
        denoised_signal = librosa.istft(D_denoised)
        
        # Step 3: Voice activity detection with more aggressive settings
        print("  Detecting voice activity...")
        # Compute energy of signal with smaller frames for better speed
        frame_length = int(0.025 * sampling_rate)  # 25ms frames
        hop_length = int(0.010 * sampling_rate)    # 10ms hop
        
        # For very long signals, sub-sample to avoid memory issues
        max_signal_length = 10 * 60 * sampling_rate  # 10 minutes max
        if len(denoised_signal) > max_signal_length:
            print("  Long signal detected, using sub-sampling for VAD...")
            subsample_factor = int(len(denoised_signal) / max_signal_length) + 1
            vad_signal = denoised_signal[::subsample_factor]
        else:
            vad_signal = denoised_signal
        
        # Compute RMS energy
        energy = librosa.feature.rms(y=vad_signal, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Determine noise floor
        energy_sorted = np.sort(energy)
        noise_floor = np.mean(energy_sorted[:int(len(energy_sorted) * 0.1)])  # Use lowest 10% as noise estimate
        
        # Set VAD threshold
        vad_threshold = noise_floor * 2.0
        
        # Create VAD mask and stretch to match original signal
        vad_mask = energy > vad_threshold
        vad_mask_full = np.zeros_like(denoised_signal, dtype=bool)
        
        # Handle long signals specially to avoid slow loops
        if len(denoised_signal) > max_signal_length:
            # Instead of exact mapping, just use blocks
            block_size = hop_length * subsample_factor
            for i, is_speech in enumerate(vad_mask):
                if is_speech:  # Only process speech frames
                    start = min(i * block_size, len(vad_mask_full) - 1)
                    end = min(start + frame_length * subsample_factor, len(vad_mask_full))
                    vad_mask_full[start:end] = True
        else:
            # Stretch mask to full signal length more efficiently
            for i, is_speech in enumerate(vad_mask):
                if is_speech:  # Only process when speech is detected
                    start = i * hop_length
                    end = min(start + frame_length, len(denoised_signal))
                    vad_mask_full[start:end] = True
        
        # Apply noise reduction to non-speech parts
        denoised_signal = denoised_signal.copy()
        denoised_signal[~vad_mask_full] *= 0.05  # More aggressive reduction
        
        # Step 4: Apply pre-emphasis filter to enhance high-frequency content
        print("  Enhancing voice characteristics...")
        pre_emphasis = 0.97
        emphasized_signal = sig_proc.lfilter([1, -pre_emphasis], [1], denoised_signal)
        
        # Step 5: Apply bandpass filter focusing on voice frequencies
        print("  Applying vocal frequency enhancement...")
        nyquist = sampling_rate / 2.0
        low_cutoff = 100 / nyquist   # Focus on vocal range
        high_cutoff = 4000 / nyquist  # Focus on main formants
        
        # Design bandpass filter - reduced order for speed
        b, a = sig_proc.butter(4, [low_cutoff, high_cutoff], btype='band')  # Lower order for speed
        filtered_signal = sig_proc.filtfilt(b, a, emphasized_signal)
        
        # Step 6: Apply dynamic range compression to boost quiet voices
        print("  Applying dynamic range compression...")
        # Compute envelope
        envelope = np.abs(sig_proc.hilbert(filtered_signal))
        # Smoothing window
        win_size = int(0.04 * sampling_rate)  # 40ms window
        win = np.ones(win_size) / win_size
        smooth_envelope = np.convolve(envelope, win, mode='same')
        
        # Apply compression
        threshold = np.mean(smooth_envelope) * 1.2
        ratio = 0.25  # Stronger compression
        compressed_signal = filtered_signal.copy()
        
        # Only compress values above threshold
        mask = smooth_envelope > threshold
        compressed_envelope = threshold + (smooth_envelope[mask] - threshold) * ratio
        compressed_signal[mask] = filtered_signal[mask] * (compressed_envelope / smooth_envelope[mask])
        
        # Step 7: Apply spectral contrast enhancement
        print("  Enhancing speaker-specific vocal traits...")
        # Use a more efficient approach with larger frames
        frame_length = int(0.03 * sampling_rate)  # 30ms frames
        hop_length = int(0.015 * sampling_rate)   # 15ms hop
        
        # Add fundamental frequency (F0) tracking for speaker identity
        print("  Tracking voice fundamental frequency...")
        # Extract pitch using a faster method than PYIN
        try:
            # Use lightweight method for F0 estimation
            f0_frames = []
            # Process fewer frames for speed (every 3rd frame)
            for i in range(0, len(compressed_signal) - frame_length, hop_length * 3):
                frame = compressed_signal[i:i+frame_length]
                frame = frame * np.hanning(len(frame))
                # FFT
                fft_mag = np.abs(np.fft.rfft(frame))
                freqs = np.fft.rfftfreq(frame_length, 1.0/sampling_rate)
                
                # Find peak in speech range (70-400 Hz)
                idx_min = np.where(freqs >= 70)[0]
                idx_max = np.where(freqs <= 400)[0]
                if len(idx_min) > 0 and len(idx_max) > 0:
                    idx_start = idx_min[0]
                    idx_end = idx_max[-1]
                    if idx_start < idx_end:
                        peak_idx = idx_start + np.argmax(fft_mag[idx_start:idx_end+1])
                        if peak_idx < len(freqs):
                            f0_est = freqs[peak_idx]
                            f0_frames.append((i, f0_est))
            
            # Create F0 curve matching the full signal length
            f0_full = np.zeros(len(compressed_signal))
            for start_idx, f0_val in f0_frames:
                end_idx = min(start_idx + frame_length, len(f0_full))
                f0_full[start_idx:end_idx] = f0_val
        except Exception as e:
            print(f"  F0 tracking simplified due to: {e}")
            f0_full = np.zeros(len(compressed_signal))
        
        # Step 8: Final normalization and enhancement
        print("  Applying final enhancements...")
        # Normalize the signal
        final_signal = librosa.util.normalize(compressed_signal)
        
        # Apply a slight boost to speech frequencies
        boost_freqs = np.array([1000, 2000, 3000]) / nyquist  # Common speech frequencies
        for freq in boost_freqs:
            b, a = sig_proc.butter(2, [freq-0.1, freq+0.1], btype='band')
            boost = sig_proc.filtfilt(b, a, final_signal)
            final_signal += boost * 0.1  # Add 10% boost
        
        # Final normalization
        final_signal = librosa.util.normalize(final_signal)
        
        print("Audio preprocessing complete.")
        return final_signal, f0_full
        
    except Exception as e:
        print(f"Audio preprocessing failed: {e}. Using original audio.")
        import traceback
        traceback.print_exc()
        return signal, np.zeros(len(signal))

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Speaker Diarization using pyannote.audio")
    parser.add_argument("input_file", nargs="?", help="Path to input audio or video file (positional argument)")
    parser.add_argument("-i", "--input", help="Path to input audio or video file")
    parser.add_argument("-s", "--speakers", type=int, help="Number of speakers (if known)")
    parser.add_argument("--min-speakers", type=int, help="Minimum number of speakers to find")
    parser.add_argument("--max-speakers", type=int, help="Maximum number of speakers to find")
    parser.add_argument("-p", "--plot", action="store_true", help="Plot diarization results")
    parser.add_argument("-o", "--output", help="Output directory (default: same as input)")
    parser.add_argument("--rttm", action="store_true", help="Output RTTM format file")
    parser.add_argument("--timeout", type=int, default=7200, help="Timeout in seconds (default: 2 hours)")
    parser.add_argument("--token", help="Path to a file containing your Hugging Face token")
    parser.add_argument("--force-cpu", action="store_true", help="Force using CPU even if GPU is available")
    parser.add_argument("--no-extract", action="store_true", help="Skip audio extraction for video files (use if already extracted)")
    
    args = parser.parse_args()
    
    # Handle both positional and named input arguments
    input_file = args.input if args.input else args.input_file
    
    if not input_file:
        parser.print_help()
        print("\nError: Input file is required. Please provide it as a positional argument or with -i/--input")
        return
    
    # Check if input file exists
    if not os.path.isfile(input_file):
        print(f"Error: Input file '{input_file}' does not exist")
        return
    
    # Apply global timeout to avoid hanging indefinitely
    import signal
    
    def timeout_handler(signum, frame):
        print("\n\nTimeout reached. The process is taking too long and will be terminated.")
        sys.exit(1)
    
    # Set the timeout handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(args.timeout)
    
    try:
        # Set output directory
        output_dir = args.output if args.output else os.path.dirname(input_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Process input file
        file_extension = os.path.splitext(input_file)[1].lower()
        audio_path = input_file
        
        # If input is a video file, extract audio
        if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m4v', '.3gp']:
            # Check if we should skip extraction (if already done previously)
            potential_audio_path = os.path.splitext(input_file)[0] + ".wav"
            
            if args.no_extract and os.path.exists(potential_audio_path):
                print(f"Using existing audio file: {potential_audio_path}")
                audio_path = potential_audio_path
            else:
                print("Extracting audio from video...")
                output_audio_path = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + ".wav")
                audio_path = extract_audio_from_video(input_file, output_audio_path)
                
                if not audio_path:
                    print("Audio extraction failed. Trying fallback method...")
                    audio_path = extract_audio_from_video(input_file, output_audio_path, fallback_method=True)
                    
                    if not audio_path:
                        print("All audio extraction methods failed.")
                        return
                
                print("Audio extraction complete")
        
        # Perform diarization
        print("Starting diarization with pyannote.audio...")
        
        # Set device based on args
        device = "cpu" if args.force_cpu else None
        
        segments = perform_diarization(
            audio_path, 
            args.speakers, 
            args.plot,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
            token_path=args.token
        )
        
        if segments:
            print(f"\nDiarization complete. {len(segments)} segments found.")
            
            # Generate RTTM file if requested
            if args.rttm:
                convert_to_rttm(segments, audio_path)
            
            # Print final segment count
            speaker_counts = {}
            for segment in segments:
                spk = segment['speaker']
                if spk not in speaker_counts:
                    speaker_counts[spk] = 0
                speaker_counts[spk] += 1
                
            print(f"Total segments: {len(segments)}")
            for spk, count in speaker_counts.items():
                print(f"Speaker {spk}: {count} segments")
        else:
            print("Diarization failed.")
        
        # Cancel the alarm when done
        signal.alarm(0)
    
    except Exception as e:
        print(f"\nError during processing: {e}")
        # Cancel the alarm
        signal.alarm(0)
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    main() 