import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import time
import uuid
import re
from tqdm import tqdm

# Check for required packages and install if missing
def check_and_install_packages():
    required_packages = {
        'numpy': 'numpy',
        'matplotlib': 'matplotlib',
        'moviepy': 'moviepy',
        'tqdm': 'tqdm',
        'hmmlearn': 'hmmlearn',
        'sklearn': 'scikit-learn',
        'scipy': 'scipy',
        'eyed3': 'eyed3',
        'pydub': 'pydub'
    }
    
    # Install pyAudioAnalysis after its dependencies are installed
    # to ensure all dependencies are available
    pyaudio_dependencies = list(required_packages.values())
    
    missing_packages = []
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"Package {package} is already installed.")
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages or not is_package_installed('pyAudioAnalysis'):
        print("Missing required packages. Installing now...")
        import subprocess
        
        # First install all dependencies
        for package in missing_packages:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
                
        # Then install pyAudioAnalysis if needed
        if not is_package_installed('pyAudioAnalysis'):
            print("Installing pyAudioAnalysis...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyAudioAnalysis"])
                print("Successfully installed pyAudioAnalysis")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install pyAudioAnalysis: {e}")
        
        print("All required packages installed successfully.")
        
        # Restart the script to ensure imports work
        print("Restarting script...")
        # Preserve original command-line args for restart
        args = sys.argv.copy()
        os.execv(sys.executable, [sys.executable] + args)

def is_package_installed(package_name):
    """Check if a package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

# Check for packages before trying to import them
check_and_install_packages()

# Now import the required packages
from moviepy.editor import VideoFileClip
from pyAudioAnalysis import audioSegmentation as aS
from pyAudioAnalysis import audioBasicIO as aIO

def extract_guid_from_filename(filename):
    """Extract GUID from filename or generate a new one if not found."""
    # Try to find a GUID pattern in the filename (standard UUID format)
    guid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    match = re.search(guid_pattern, filename, re.IGNORECASE)
    
    if match:
        return match.group(0)
    else:
        # Generate a new GUID if not found
        return str(uuid.uuid4())

def extract_audio_from_video(video_path, audio_output_path=None):
    """Extract audio from video file and save as WAV."""
    if audio_output_path is None:
        audio_output_path = os.path.splitext(video_path)[0] + ".wav"
    
    try:
        print("Extracting audio from video...")
        
        # Create a simple progress indicator
        sys.stdout.write("Starting audio extraction...\n")
        
        # Load the video file
        video = VideoFileClip(video_path)
        
        # Simply disable the logger to avoid compatibility issues
        # We'll create our own simple progress display
        print("This may take a moment depending on the video size...")
        
        # Use a simple animated progress indicator
        import threading
        import itertools
        import time
        
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
        
        print(f"Audio extracted and saved to {audio_output_path}")
        return audio_output_path
    except Exception as e:
        print(f"Error extracting audio from video: {e}")
        import traceback
        traceback.print_exc()
        return None

def perform_segmentation(audio_path, num_speakers=2, plot=False):
    """Perform speaker segmentation on the given audio file."""
    try:
        # Load audio file
        print("Loading audio file...")
        sampling_rate, signal = aIO.read_audio_file(audio_path)
        
        # Convert stereo to mono if needed
        if len(signal.shape) > 1 and signal.shape[1] > 1:
            print("Converting stereo audio to mono...")
            signal = np.mean(signal, axis=1)
        
        duration = len(signal) / float(sampling_rate)
        print(f"Audio duration: {duration:.2f} seconds")
        
        # Perform speaker segmentation with progress updates
        print(f"Performing audio segmentation (expected segments: {num_speakers})...")
        print("This may take some time depending on the audio length...")
        
        # Create progress bar
        progress_bar = tqdm(total=100, desc="Processing progress", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
        
        # Start time for progress estimation
        start_time = time.time()
        
        # Update progress to 10%
        progress_bar.update(10)
        
        # Use custom audio analysis approach
        print("Analyzing audio features...")
        
        # Define the window and step sizes for analysis
        window_size = int(0.5 * sampling_rate)  # 500ms windows
        step_size = int(0.25 * sampling_rate)  # 250ms step
        
        # Create empty arrays to store audio features
        energy_curve = []
        spectral_centroid = []
        zero_crossing_rate = []
        
        # Process the audio in windows
        progress_bar.update(10)  # Update to 20%
        print("Analyzing audio features...")
        
        for i in range(0, len(signal) - window_size, step_size):
            # Extract window
            window = signal[i:i + window_size]
            
            # Calculate energy (volume)
            energy = np.sum(window ** 2) / window_size
            energy_curve.append(energy)
            
            # Calculate spectral centroid (brightness)
            if energy > 0.0001:  # Only for non-silent segments
                fft_mag = np.abs(np.fft.rfft(window))
                freqs = np.fft.rfftfreq(window_size, 1.0/sampling_rate)
                
                # Ensure both arrays have the same shape
                min_length = min(len(freqs), len(fft_mag))
                centroid = np.sum(freqs[:min_length] * fft_mag[:min_length]) / np.sum(fft_mag[:min_length]) if np.sum(fft_mag[:min_length]) > 0 else 0
                spectral_centroid.append(centroid)
            else:
                spectral_centroid.append(0)
            
            # Calculate zero crossing rate (an indicator of voice vs. unvoiced sounds)
            zcr = np.sum(np.abs(np.diff(np.signbit(window)))) / window_size
            zero_crossing_rate.append(zcr)
        
        # Update progress
        progress_bar.update(30)  # Update to 50%
        print("Detecting segment boundaries...")
        
        # Normalize the features
        if len(energy_curve) > 0:
            energy_min = np.min(energy_curve)
            energy_range = np.max(energy_curve) - energy_min
            energy_norm = (energy_curve - energy_min) / (energy_range + 1e-10)
            
            spectral_min = np.min(spectral_centroid)
            spectral_range = np.max(spectral_centroid) - spectral_min
            spectral_norm = (spectral_centroid - spectral_min) / (spectral_range + 1e-10)
            
            zcr_min = np.min(zero_crossing_rate)
            zcr_range = np.max(zero_crossing_rate) - zcr_min
            zcr_norm = (zero_crossing_rate - zcr_min) / (zcr_range + 1e-10)
            
            # Combine features to create a change detection curve
            feature_vector = np.column_stack((energy_norm, spectral_norm, zcr_norm))
            
            # Calculate the distance between adjacent windows
            change_curve = np.zeros(len(feature_vector) - 1)
            for i in range(len(change_curve)):
                change_curve[i] = np.linalg.norm(feature_vector[i+1] - feature_vector[i])
            
            # Smooth the change curve
            window_len = 5
            if len(change_curve) > window_len:
                smoothed_curve = np.convolve(change_curve, np.ones(window_len)/window_len, mode='same')
            else:
                smoothed_curve = change_curve
            
            # Detect peaks in the change curve (segment boundaries)
            threshold = np.mean(smoothed_curve) + 0.5 * np.std(smoothed_curve)
            change_points = [i for i in range(1, len(smoothed_curve)-1) 
                            if smoothed_curve[i] > threshold and 
                            smoothed_curve[i] > smoothed_curve[i-1] and 
                            smoothed_curve[i] > smoothed_curve[i+1]]
            
            # Ensure we have a reasonable number of segments
            min_segments = num_speakers * 2  # At least 2 segments per speaker
            
            if len(change_points) < min_segments:
                # If we don't have enough segments, add more based on energy changes
                energy_changes = np.abs(np.diff(energy_norm))
                energy_changes_sorted = np.argsort(energy_changes)[::-1]  # Sort in descending order
                
                # Add the top energy change points that aren't already in change_points
                for idx in energy_changes_sorted:
                    if idx not in change_points and idx > 0 and idx < len(smoothed_curve)-1:
                        change_points.append(idx)
                        if len(change_points) >= min_segments:
                            break
                
                # Sort the change points by position
                change_points.sort()
        else:
            # Fallback if feature extraction failed
            change_points = []
            for i in range(num_speakers * 2):
                change_points.append(int(i * len(signal) / (num_speakers * 2)))
        
        # Update progress
        progress_bar.update(20)  # Update to 70%
        print("Finalizing segments...")
        
        # Convert change points to timestamps
        change_timestamps = [i * step_size / sampling_rate for i in change_points]
        
        # Create segments based on change points
        segment_boundaries = [0] + change_timestamps + [duration]
        segment_boundaries.sort()
        
        # Simple feature extraction for each segment
        segment_features = []
        valid_segments = []
        
        for i in range(len(segment_boundaries) - 1):
            start_idx = int(segment_boundaries[i] * sampling_rate)
            end_idx = int(segment_boundaries[i+1] * sampling_rate)
            
            if end_idx > len(signal):
                end_idx = len(signal)
            
            if start_idx >= end_idx:
                continue
                
            segment_signal = signal[start_idx:end_idx]
            
            # Calculate energy for this segment
            segment_energy = np.mean(segment_signal ** 2)
            
            # Only include segments with sufficient energy (not silence)
            if segment_energy > 0.0001 and len(segment_signal) > 0:
                # Calculate basic spectral feature
                if len(segment_signal) >= 512:
                    fft_mag = np.abs(np.fft.rfft(segment_signal[:512]))
                    freqs = np.fft.rfftfreq(512, 1.0/sampling_rate)
                    min_length = min(len(freqs), len(fft_mag))
                    
                    # Spectral centroid (brightness)
                    centroid = np.sum(freqs[:min_length] * fft_mag[:min_length]) / np.sum(fft_mag[:min_length]) if np.sum(fft_mag[:min_length]) > 0 else 0
                else:
                    centroid = 0
                
                # Add to features list
                segment_features.append([segment_energy, centroid])
                valid_segments.append(i)
        
        # Assign segment IDs (no specific speaker labels)
        # We'll just create chronological segments
        segment_ids = np.zeros(len(segment_boundaries) - 1, dtype=int)
        
        # Update progress
        progress_bar.update(20)  # Update to 90%
        
        # Create frame-level segment assignments (10 frames per second)
        frame_rate = 10
        frame_count = int(duration * frame_rate)
        flags = np.zeros(frame_count)
        
        # Complete the progress bar
        progress_bar.update(10)  # Update to 100%
        progress_bar.close()
        
        # Calculate actual processing time
        processing_time = time.time() - start_time
        print(f"Segmentation completed in {processing_time:.2f} seconds")
        
        # Get segment information
        print("Processing segment data...")
        segments = []
        for i in range(len(segment_boundaries) - 1):
            # Create segment with start/end times
            segment = {
                "id": i,
                "start": round(segment_boundaries[i], 2),
                "end": round(segment_boundaries[i+1], 2),
                "duration": round(segment_boundaries[i+1] - segment_boundaries[i], 2)
            }
            segments.append(segment)
        
        # Print segmentation results
        print("\nSegmentation Results:")
        print("--------------------")
        total_duration = 0
        
        for i, segment in enumerate(segments):
            duration = segment['duration']
            total_duration += duration
            print(f"Segment {i+1}: {segment['start']}s to {segment['end']}s (Duration: {duration}s)")
        
        print(f"\nTotal Duration: {total_duration:.2f}s")
        print(f"Number of segments: {len(segments)}")
        
        # Plot results if requested
        if plot:
            plot_segmentation(segment_boundaries, audio_path)
        
        return segments
    
    except Exception as e:
        print(f"Error performing segmentation: {e}")
        import traceback
        traceback.print_exc()
        return None

def plot_segmentation(segment_boundaries, audio_path):
    """Plot the segmentation results."""
    try:
        print("Generating segmentation plot...")
        plt.figure(figsize=(15, 4))
        
        # Plot segment boundaries as vertical lines
        for boundary in segment_boundaries:
            plt.axvline(x=boundary, color='r', linestyle='-')
        
        # Add labels
        plt.xlabel("Time (seconds)")
        plt.ylabel("Segment Boundaries")
        plt.title(f"Audio Segmentation for {os.path.basename(audio_path)}")
        plt.ylim([0, 1])  # Just to have a visible plot
        plt.grid(True)
        
        # Save plot
        plot_path = os.path.splitext(audio_path)[0] + "_segmentation.png"
        plt.savefig(plot_path)
        print(f"Segmentation plot saved to {plot_path}")
        plt.show()
    except Exception as e:
        print(f"Error plotting segmentation results: {e}")

def save_transcript(segments, audio_path, guid=None):
    """Save segmentation results to the transcript directory."""
    try:
        # Create transcript directory if it doesn't exist
        transcript_dir = os.path.join(os.path.dirname(os.path.dirname(audio_path)), "transcript")
        os.makedirs(transcript_dir, exist_ok=True)
        
        # Use GUID from filename or parameter, or generate one
        if guid is None:
            guid = extract_guid_from_filename(os.path.basename(audio_path))
        
        # Create output filename with GUID
        output_path = os.path.join(transcript_dir, f"{guid}_segments.txt")
        
        print(f"Saving transcript to {output_path}...")
        with open(output_path, 'w') as file:
            file.write(f"Audio Segmentation Results\n")
            file.write(f"=========================\n\n")
            file.write(f"File: {audio_path}\n")
            file.write(f"GUID: {guid}\n\n")
            file.write(f"Segments:\n")
            
            for i, segment in enumerate(segments):
                file.write(f"[{segment['start']:.2f} - {segment['end']:.2f}] Duration: {segment['duration']:.2f}s\n")
        
        print(f"Transcript saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving transcript: {e}")
        return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Speaker Segmentation Tool")
    parser.add_argument("input_file", nargs="?", help="Path to input audio or video file (positional argument)")
    parser.add_argument("-i", "--input", help="Path to input audio or video file")
    parser.add_argument("-s", "--segments", type=int, default=2, help="Expected number of segments (default: 2)")
    parser.add_argument("-p", "--plot", action="store_true", help="Plot segmentation results")
    parser.add_argument("-o", "--output", help="Output directory (default: same as input)")
    parser.add_argument("-g", "--guid", help="Specific GUID to use (optional, will be extracted from filename or generated)")
    
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
    
    # Set output directory
    output_dir = args.output if args.output else os.path.dirname(input_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get or generate GUID
    guid = args.guid if args.guid else extract_guid_from_filename(os.path.basename(input_file))
    print(f"Using GUID: {guid}")
    
    # Process input file
    file_extension = os.path.splitext(input_file)[1].lower()
    audio_path = input_file
    
    # If input is a video file, extract audio
    if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.flv']:
        print("Video file detected. Extracting audio...")
        output_audio_path = os.path.join(output_dir, f"{guid}.wav")
        audio_path = extract_audio_from_video(input_file, output_audio_path)
        if not audio_path:
            return
    
    # Perform segmentation
    segments = perform_segmentation(audio_path, args.segments, args.plot)
    
    # Save results to file
    if segments:
        save_transcript(segments, audio_path, guid)
        print("\nSegmentation process completed successfully!")

if __name__ == "__main__":
    main() 