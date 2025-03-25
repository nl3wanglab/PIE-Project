import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import time
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
        'pydub': 'pydub',
        'librosa': 'librosa'  # Adding librosa for advanced audio processing
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

def preprocess_audio(signal, sampling_rate, fast_mode=True):
    """Apply audio preprocessing to enhance speaker differentiation."""
    print("Applying audio preprocessing to enhance speaker detection...")
    
    try:
        import librosa
        from scipy import signal as sig_proc
        
        # Step 1: Normalize audio
        print("  Normalizing audio levels...")
        normalized_signal = librosa.util.normalize(signal)
        
        # Step 2: Voice activity detection with more aggressive settings
        print("  Detecting voice activity...")
        # Compute energy of signal with smaller frames for better speed
        frame_length = int(0.025 * sampling_rate)  # 25ms frames
        hop_length = int(0.010 * sampling_rate)    # 10ms hop
        
        # For very long signals, sub-sample to avoid memory issues
        max_signal_length = 10 * 60 * sampling_rate  # 10 minutes max
        if len(normalized_signal) > max_signal_length:
            print("  Long signal detected, using sub-sampling for VAD...")
            subsample_factor = int(len(normalized_signal) / max_signal_length) + 1
            vad_signal = normalized_signal[::subsample_factor]
        else:
            vad_signal = normalized_signal
        
        # Compute RMS energy
        energy = librosa.feature.rms(y=vad_signal, frame_length=frame_length, hop_length=hop_length)[0]
        
        # Determine noise floor
        energy_sorted = np.sort(energy)
        noise_floor = np.mean(energy_sorted[:int(len(energy_sorted) * 0.1)])  # Use lowest 10% as noise estimate
        
        # Set VAD threshold
        vad_threshold = noise_floor * 2.0
        
        # Create VAD mask and stretch to match original signal
        vad_mask = energy > vad_threshold
        vad_mask_full = np.zeros_like(normalized_signal, dtype=bool)
        
        # Handle long signals specially to avoid slow loops
        if len(normalized_signal) > max_signal_length:
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
                    end = min(start + frame_length, len(normalized_signal))
                    vad_mask_full[start:end] = True
        
        # Apply noise reduction to non-speech parts
        denoised_signal = normalized_signal.copy()
        denoised_signal[~vad_mask_full] *= 0.05  # More aggressive reduction
        
        # Step 3: Apply pre-emphasis filter to enhance high-frequency content
        print("  Enhancing voice characteristics...")
        pre_emphasis = 0.97
        emphasized_signal = sig_proc.lfilter([1, -pre_emphasis], [1], denoised_signal)
        
        # Step 4: Apply bandpass filter focusing on voice frequencies
        print("  Applying vocal frequency enhancement...")
        nyquist = sampling_rate / 2.0
        low_cutoff = 100 / nyquist   # Focus on vocal range
        high_cutoff = 4000 / nyquist  # Focus on main formants
        
        # Design bandpass filter - reduced order for speed
        b, a = sig_proc.butter(4, [low_cutoff, high_cutoff], btype='band')  # Lower order for speed
        filtered_signal = sig_proc.filtfilt(b, a, emphasized_signal)
        
        # Very fast mode for long files
        duration = len(filtered_signal) / sampling_rate
        if duration > 300:  # 5+ minutes
            print("  Using simplified processing for long audio...")
            fast_mode = True  # Force fast mode for long files
        
        # Fast mode skips the most computationally intensive parts
        if fast_mode:
            print("  Using fast mode for audio preprocessing...")
            # Extract approximate F0 (fundamental frequency) quickly
            # Use the zero crossing rate as a rough approximation of frequency content
            f0_approx = np.zeros(len(filtered_signal))
            
            # For long files, use sparse sampling to estimate F0
            if duration > 300:  # 5+ minutes
                zcr_win_size = int(0.04 * sampling_rate)  # Larger window
                zcr_hop_size = int(0.02 * sampling_rate) * 5  # Much larger hop for speed
                
                # Calculate ZCR only at sparse intervals for speed
                total_frames = (len(filtered_signal) - zcr_win_size) // zcr_hop_size
                print(f"  Processing {total_frames} frames for pitch estimation...")
                
                # Process with progress updates for long files
                for i_frame in range(0, total_frames):
                    if i_frame % 100 == 0:
                        print(f"  Pitch processing: {i_frame}/{total_frames} frames...\r", end='')
                    
                    i = i_frame * zcr_hop_size
                    if i + zcr_win_size <= len(filtered_signal):
                        frame = filtered_signal[i:i+zcr_win_size]
                        # Simple ZCR calculation
                        zcr = np.sum(np.abs(np.diff(np.signbit(frame)))) / zcr_win_size
                        # Rough mapping from ZCR to frequency
                        freq_est = zcr * sampling_rate / 2
                        # Constrain to reasonable vocal range
                        if 60 <= freq_est <= 400:
                            start_idx = i
                            end_idx = min(i + zcr_hop_size, len(f0_approx))
                            f0_approx[start_idx:end_idx] = freq_est
                print()  # New line after progress
            else:
                # For shorter files, use more accurate processing
                zcr_win_size = int(0.02 * sampling_rate)
                zcr_hop_size = int(0.01 * sampling_rate)
                
                # Calculate ZCR only every zcr_hop_size samples for speed
                for i in range(0, len(filtered_signal) - zcr_win_size, zcr_hop_size):
                    frame = filtered_signal[i:i+zcr_win_size]
                    # Simple ZCR calculation
                    zcr = np.sum(np.abs(np.diff(np.signbit(frame)))) / zcr_win_size
                    # Rough mapping from ZCR to frequency
                    freq_est = zcr * sampling_rate / 2
                    # Constrain to reasonable vocal range
                    if 60 <= freq_est <= 400:
                        f0_approx[i:i+zcr_hop_size] = freq_est
            
            # Apply simple spectral contrast enhancement
            print("  Applying basic spectral enhancement...")
            final_signal = filtered_signal  # Skip detailed spectral processing
            
            print("Fast audio preprocessing complete.")
            return final_signal, f0_approx
        
        # Full mode with more detailed processing
        else:
            print("  Applying advanced vocal enhancement...")
            # Compute envelope
            envelope = np.abs(sig_proc.hilbert(filtered_signal))
            # Smoothing window
            win_size = int(0.04 * sampling_rate)  # Increased from 30ms to 40ms for better speed
            win = np.ones(win_size) / win_size
            smooth_envelope = np.convolve(envelope, win, mode='same')
            
            # Apply compression
            threshold = np.mean(smooth_envelope) * 1.2
            ratio = 0.25
            compressed_signal = filtered_signal.copy()
            
            # Only compress values above threshold
            mask = smooth_envelope > threshold
            compressed_envelope = threshold + (smooth_envelope[mask] - threshold) * ratio
            compressed_signal[mask] = filtered_signal[mask] * (compressed_envelope / smooth_envelope[mask])
            
            # Step 6: Spectral contrast enhancement (optimized)
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
            
            # Efficient spectral contrast enhancement - process fewer frames
            # Only process every 3rd frame for speed
            step = 3  # Process every 3rd frame
            frames = librosa.util.frame(compressed_signal, frame_length=frame_length, 
                                       hop_length=hop_length * step)
            
            # Final signal
            enhanced_signal = compressed_signal.copy()  # Start with compressed signal
            
            # Process select frames for efficiency
            n_frames_to_process = min(100, frames.shape[1])  # Limit number of frames
            if n_frames_to_process > 0:
                frames_to_process = np.linspace(0, frames.shape[1]-1, n_frames_to_process, dtype=int)
                
                for i in frames_to_process:
                    frame = frames[:, i]
                    # Calculate FFT
                    frame_fft = np.fft.rfft(frame)
                    frame_mag = np.abs(frame_fft)
                    frame_phase = np.angle(frame_fft)
                    
                    # Simple spectral contrast - skip median filtering for speed
                    enhanced_mag = np.power(frame_mag, 1.5)  # Simple power-law enhancement
                    
                    # Reconstruct frame
                    enhanced_fft = enhanced_mag * np.exp(1j * frame_phase)
                    enhanced_frame = np.fft.irfft(enhanced_fft)
                    
                    # Apply to original signal
                    if len(enhanced_frame) >= frame_length:
                        start = i * hop_length * step
                        end = start + frame_length
                        if end <= len(enhanced_signal):
                            enhanced_signal[start:end] += enhanced_frame[:frame_length] * 0.5  # Blend with original
            
            # Step 7: Final normalization
            final_signal = librosa.util.normalize(enhanced_signal)
            
            print("Detailed audio preprocessing complete.")
            return final_signal, f0_full
        
    except Exception as e:
        print(f"Audio preprocessing failed: {e}. Using original audio.")
        import traceback
        traceback.print_exc()
        return signal, np.zeros(len(signal))

def extract_segment_features(segment_frames, energy_norm, spectral_centroid_norm, spectral_rolloff_norm, 
                           zcr_norm, spectral_flux_norm, harmonicity_norm, mfcc_norm, 
                           segment_duration, f0_contour=None, segment_boundaries=None, i=None, sampling_rate=None):
    """Extract features for a segment - separate function to improve maintainability and performance"""
    # Energy stats (level and variation)
    energy_mean = np.mean(energy_norm[segment_frames])
    energy_std = np.std(energy_norm[segment_frames]) if len(segment_frames) > 1 else 0
    energy_max = np.max(energy_norm[segment_frames])
    
    # Spectral centroid (pitch) stats
    centroid_mean = np.mean(spectral_centroid_norm[segment_frames])
    centroid_std = np.std(spectral_centroid_norm[segment_frames]) if len(segment_frames) > 1 else 0
    
    # Spectral rolloff (voice brightness/timbre)
    rolloff_mean = np.mean(spectral_rolloff_norm[segment_frames])
    
    # ZCR (consonant vs vowel characteristics)
    zcr_mean = np.mean(zcr_norm[segment_frames])
    zcr_std = np.std(zcr_norm[segment_frames]) if len(segment_frames) > 1 else 0
    
    # Spectral flux (voice variation)
    flux_mean = np.mean(spectral_flux_norm[segment_frames])
    
    # Harmonicity (voice quality)
    harm_mean = np.mean(harmonicity_norm[segment_frames])
    
    # MFCC stats (voice timbre/identity)
    start_frame = segment_frames[0]
    end_frame = segment_frames[-1] + 1
    if start_frame < len(mfcc_norm) and end_frame <= len(mfcc_norm):
        mfcc_means = np.mean(mfcc_norm[start_frame:end_frame], axis=0)
    else:
        mfcc_means = np.zeros(13)
    
    # Initialize pitch features
    pitch_features = [0, 0, 0, 0]
    valid_pitch = False
    
    # Extract F0 (pitch) statistics for this segment if available
    if f0_contour is not None and len(f0_contour) > 0 and segment_boundaries is not None and i is not None and sampling_rate is not None:
        try:
            # Calculate segment start and end indices in samples
            start_idx = int(segment_boundaries[i] * sampling_rate)
            end_idx = int(segment_boundaries[i+1] * sampling_rate)
            
            # Ensure we don't exceed array bounds
            start_idx = max(0, min(start_idx, len(f0_contour) - 1))
            end_idx = max(start_idx + 1, min(end_idx, len(f0_contour)))
            
            # Extract pitch features for this segment
            segment_f0 = f0_contour[start_idx:end_idx]
            
            # Only consider non-zero pitch values
            valid_f0 = segment_f0[segment_f0 > 0]
            
            if len(valid_f0) > 0:
                # Calculate pitch statistics
                f0_mean = np.mean(valid_f0)
                f0_std = np.std(valid_f0) if len(valid_f0) > 1 else 0
                f0_range = np.max(valid_f0) - np.min(valid_f0) if len(valid_f0) > 1 else 0
                
                # F0 contour shape features - rising/falling patterns
                if len(valid_f0) > 2:
                    # Simple linear regression slope
                    x = np.arange(len(valid_f0))
                    slope = np.polyfit(x, valid_f0, 1)[0]
                else:
                    slope = 0
                
                pitch_features = [f0_mean, f0_std, f0_range, slope]
                valid_pitch = True
        except Exception as e:
            # Just log and continue - pitch is helpful but not essential
            print(f"  Pitch extraction warning: {e}")
    
    # Create feature vector for speaker identification with weighted components
    features = [
        energy_mean * 1.0,     # Normal weight
        energy_std * 1.0, 
        energy_max * 1.0,
        centroid_mean * 2.0,   # Double weight for pitch mean
        centroid_std * 1.5,    # Higher weight for pitch variation
        rolloff_mean * 1.2,
        zcr_mean * 1.5,        # Higher weight for consonants
        zcr_std * 1.2,
        flux_mean * 1.2,
        harm_mean * 1.5,       # Higher weight for voice quality
        segment_duration * 0.5 # Less weight on duration
    ]
    
    # Add pitch features if available
    if valid_pitch:
        for pf in pitch_features:
            features.append(pf * 3.0)  # Triple weight for F0 features
    
    # Add MFCC features
    weighted_mfcc = [m * 2.0 for m in mfcc_means]  # Double weight for MFCCs
    features.extend(weighted_mfcc)
    
    return features, valid_pitch

def perform_diarization(audio_path, num_speakers=2, plot=True, fast_mode=False):
    """Perform speaker diarization on the given audio file with enhanced speaker differentiation."""
    try:
        # Import timing modules
        import time
        
        # Start time tracking for the entire process
        global_start_time = time.time()
        
        # Load audio file
        sampling_rate, signal = aIO.read_audio_file(audio_path)
        
        # Convert stereo to mono if needed
        if len(signal.shape) > 1 and signal.shape[1] > 1:
            signal = np.mean(signal, axis=1)
        
        # Apply audio preprocessing for better speaker differentiation
        signal, f0_contour = preprocess_audio(signal, sampling_rate, fast_mode=fast_mode)
        
        duration = len(signal) / float(sampling_rate)
        
        # Maintain consistent parameters regardless of file length
        window_size = int(0.10 * sampling_rate)  # 100ms windows for best precision
        step_size = int(0.02 * sampling_rate)    # 20ms steps for best precision
        
        # Create progress bar
        progress_bar = tqdm(total=100, desc="Processing", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
        progress_bar.update(5)
        
        # Create empty arrays to store audio features
        energy_curve = []
        spectral_centroid = []
        spectral_rolloff = []
        spectral_flux = []
        zero_crossing_rate = []
        mfcc_features = []
        harmonicity = []
        
        # Progress tracking
        total_windows = (len(signal) - window_size) // step_size
        processed_windows = 0
        next_progress_update = 5
        
        # Update progress to 10%
        progress_bar.update(5)  # Now at 10%
        
        # Process the audio in windows
        for i in range(0, len(signal) - window_size, step_size):
            # Extract window
            window = signal[i:i + window_size]
            
            # Calculate energy (volume)
            energy = np.sum(window ** 2) / window_size
            energy_curve.append(energy)
            
            if energy > 0.00005:  # More sensitive threshold (reduced from 0.0001)
                # Compute FFT
                fft_mag = np.abs(np.fft.rfft(window))
                freqs = np.fft.rfftfreq(window_size, 1.0/sampling_rate)
                
                # Ensure both arrays have the same shape
                min_length = min(len(freqs), len(fft_mag))
                
                # Spectral centroid (pitch/brightness)
                if np.sum(fft_mag[:min_length]) > 0:
                    centroid = np.sum(freqs[:min_length] * fft_mag[:min_length]) / np.sum(fft_mag[:min_length])
                else:
                    centroid = 0
                spectral_centroid.append(centroid)
                
                # Spectral rolloff (measure of high-frequency content)
                cumsum = np.cumsum(fft_mag[:min_length])
                rolloff_point = 0.85 * cumsum[-1]  # 85% of energy
                rolloff_idx = np.where(cumsum >= rolloff_point)[0][0] if len(np.where(cumsum >= rolloff_point)[0]) > 0 else 0
                rolloff = freqs[rolloff_idx] if rolloff_idx < len(freqs) else 0
                spectral_rolloff.append(rolloff)
                
                # Spectral flux (frame-to-frame spectral change)
                if i > 0:
                    prev_window = signal[i - step_size:i - step_size + window_size]
                    prev_fft_mag = np.abs(np.fft.rfft(prev_window))
                    min_flux_length = min(len(fft_mag), len(prev_fft_mag))
                    flux = np.sum((fft_mag[:min_flux_length] - prev_fft_mag[:min_flux_length]) ** 2)
                else:
                    flux = 0
                spectral_flux.append(flux)
                
                # Basic MFCC-like features
                # Use mel-scale filterbank (perceptually meaningful for human voice)
                num_mel_filters = 26
                mel_min = 300  # Hz
                mel_max = min(4000, sampling_rate/2)  # Hz, cap at Nyquist
                
                # Convert to mel scale
                def hz_to_mel(hz):
                    return 2595 * np.log10(1 + hz/700)
                
                def mel_to_hz(mel):
                    return 700 * (10**(mel/2595) - 1)
                
                # Create mel filterbank
                mel_min_val = hz_to_mel(mel_min)
                mel_max_val = hz_to_mel(mel_max)
                mel_points = np.linspace(mel_min_val, mel_max_val, num_mel_filters + 2)
                hz_points = mel_to_hz(mel_points)
                bin_indices = np.floor((window_size + 1) * hz_points / sampling_rate).astype(int)
                
                # Apply mel filterbank
                mel_energies = np.zeros(num_mel_filters)
                for j in range(num_mel_filters):
                    start_idx = bin_indices[j]
                    peak_idx = bin_indices[j+1]
                    end_idx = bin_indices[j+2]
                    
                    # Ensure indices are within bounds
                    start_idx = max(0, min(start_idx, min_length-1))
                    peak_idx = max(0, min(peak_idx, min_length-1))
                    end_idx = max(0, min(end_idx, min_length-1))
                    
                    # Left slope
                    if peak_idx > start_idx:
                        left_slope = np.linspace(0, 1, peak_idx - start_idx)
                        if start_idx < min_length and peak_idx <= min_length:
                            mel_energies[j] += np.sum(fft_mag[start_idx:peak_idx] * left_slope)
                    
                    # Right slope
                    if end_idx > peak_idx:
                        right_slope = np.linspace(1, 0, end_idx - peak_idx)
                        if peak_idx < min_length and end_idx <= min_length:
                            mel_energies[j] += np.sum(fft_mag[peak_idx:end_idx] * right_slope)
                
                # Convert to log scale and take DCT (simplified MFCC)
                log_mel_energies = np.log10(mel_energies + 1e-10)
                
                # Take first 13 coefficients
                mfcc = log_mel_energies[:13]
                mfcc_features.append(mfcc)
                
                # Harmonicity (periodicity measure - helps distinguish voiced/unvoiced)
                # Calculate autocorrelation
                autocorrelation = np.correlate(window, window, mode='full')
                autocorrelation = autocorrelation[len(window)-1:] / np.max(autocorrelation)
                
                # Find peaks in autocorrelation
                peaks = []
                for j in range(1, len(autocorrelation)-1):
                    if autocorrelation[j] > autocorrelation[j-1] and autocorrelation[j] > autocorrelation[j+1]:
                        peaks.append((j, autocorrelation[j]))
                
                # Sort peaks by amplitude
                peaks.sort(key=lambda x: x[1], reverse=True)
                
                # Calculate harmonicity as ratio of second peak to first peak
                if len(peaks) >= 2 and peaks[0][1] > 0.1:  # Only if we have strong peaks
                    harmonicity.append(peaks[1][1] / peaks[0][1])
                else:
                    harmonicity.append(0)
            else:
                # For silent segments, use zeros
                spectral_centroid.append(0)
                spectral_rolloff.append(0)
                spectral_flux.append(0)
                mfcc_features.append(np.zeros(13))
                harmonicity.append(0)
            
            # Calculate zero crossing rate
            zcr = np.sum(np.abs(np.diff(np.signbit(window)))) / window_size
            zero_crossing_rate.append(zcr)
            
            # Update progress periodically
            processed_windows += 1
            progress_percent = int(25 * processed_windows / total_windows)
            if progress_percent >= next_progress_update:
                progress_bar.update(progress_percent - progress_bar.n + 10)  # Update from current progress
                next_progress_update = progress_percent + 1
        
        # Ensure progress bar is at least at 35%
        if progress_bar.n < 35:
            progress_bar.update(35 - progress_bar.n)
        
        print("Analyzing speech patterns...")
        
        # Normalize the features
        if len(energy_curve) > 0:
            # Function to normalize features
            def normalize_feature(feature):
                feature_min = np.min(feature)
                feature_range = np.max(feature) - feature_min
                if feature_range > 0:
                    return (feature - feature_min) / feature_range
                else:
                    return np.zeros_like(feature)
            
            # Normalize all features
            energy_norm = normalize_feature(energy_curve)
            spectral_centroid_norm = normalize_feature(spectral_centroid)
            spectral_rolloff_norm = normalize_feature(spectral_rolloff)
            spectral_flux_norm = normalize_feature(spectral_flux)
            zcr_norm = normalize_feature(zero_crossing_rate)
            harmonicity_norm = normalize_feature(harmonicity)
            
            # Normalize MFCC features
            mfcc_array = np.array(mfcc_features)
            mfcc_norm = np.zeros_like(mfcc_array)
            for j in range(mfcc_array.shape[1]):
                mfcc_norm[:, j] = normalize_feature(mfcc_array[:, j])
            
            # Combine features to detect speaker changes
            # Weight features for better detection of quick changes
            change_detection_features = np.column_stack((
                energy_norm * 1.5,             # Slightly reduced (from 2.0)
                spectral_centroid_norm * 2.5,  # Increased weight for pitch (from 2.0 to 2.5)
                zcr_norm * 1.8,                # Increased for consonants (from 1.5 to 1.8)
                spectral_flux_norm * 2.0,      # Increased for transitions (from 1.5 to 2.0)
                harmonicity_norm * 1.5         # Increased for voice quality (from 1.2 to 1.5)
            ))
            
            # Update progress
            progress_bar.update(5)  # Now at 40%
            
            # Calculate the distance between adjacent windows
            change_curve = np.zeros(len(change_detection_features) - 1)
            for i in range(len(change_curve)):
                change_curve[i] = np.linalg.norm(change_detection_features[i+1] - change_detection_features[i])
            
            # Even smaller smoothing window for minimal smoothing
            window_len = min(3, max(1, len(change_curve) // 800))  # Greatly reduced (from 5 max to 3 max)
            if len(change_curve) > window_len:
                smoothed_curve = np.convolve(change_curve, np.ones(window_len)/window_len, mode='same')
            else:
                smoothed_curve = change_curve
            
            # Update progress
            progress_bar.update(5)  # Now at 45%
            
            # Even more sensitive threshold for change detection
            threshold = np.mean(smoothed_curve) + 0.3 * np.std(smoothed_curve)  # Reduced (from 0.4 to 0.3)
            
            # Find all peaks above threshold
            change_points = []
            for i in range(2, len(smoothed_curve)-2):
                if (smoothed_curve[i] > threshold and 
                    smoothed_curve[i] > smoothed_curve[i-1] and 
                    smoothed_curve[i] > smoothed_curve[i-2] and  # Check two points before
                    smoothed_curve[i] > smoothed_curve[i+1] and
                    smoothed_curve[i] > smoothed_curve[i+2]):    # Check two points after
                    change_points.append(i)
            
            # Ensure we have a reasonable number of segments
            min_segments = max(5, num_speakers * 3)  # At least 3 segments per speaker, minimum 5
            max_segments = min(200, int(duration / 5))  # Max 1 segment per 5 seconds, cap at 200
            
            if len(change_points) < min_segments:
                # If we don't have enough segments, add more based on changes in features
                all_changes = []
                for i in range(1, len(smoothed_curve)-1):
                    if (smoothed_curve[i] > np.mean(smoothed_curve) and 
                        smoothed_curve[i] > smoothed_curve[i-1] and 
                        smoothed_curve[i] > smoothed_curve[i+1]):
                        all_changes.append((i, smoothed_curve[i]))
                
                # Sort by strength of change
                all_changes.sort(key=lambda x: x[1], reverse=True)
                
                # Add strong changes that aren't already in change_points
                for idx, _ in all_changes:
                    if idx not in change_points:
                        change_points.append(idx)
                        if len(change_points) >= min_segments:
                            break
                
                # Sort the change points by position
                change_points.sort()
                
            elif len(change_points) > max_segments:
                # If we have too many segments, keep only the strongest changes
                changes_with_scores = [(i, smoothed_curve[i]) for i in change_points]
                changes_with_scores.sort(key=lambda x: x[1], reverse=True)
                change_points = [x[0] for x in changes_with_scores[:max_segments]]
                change_points.sort()
                
            # Update progress
            progress_bar.update(5)  # Now at 50%
            
            # Convert change points to timestamps
            change_timestamps = [i * step_size / sampling_rate for i in change_points]
            
            # Create segments based on change points
            segment_boundaries = [0] + change_timestamps + [duration]
            segment_boundaries.sort()
            
            # Merge segments that are very close (reduced even further for rapid exchanges)
            min_segment_duration = 0.05  # 50ms - extremely short (reduced from 100ms)
            merged_boundaries = [segment_boundaries[0]]
            
            for i in range(1, len(segment_boundaries)):
                if segment_boundaries[i] - merged_boundaries[-1] >= min_segment_duration:
                    merged_boundaries.append(segment_boundaries[i])
            
            segment_boundaries = merged_boundaries
            
            # Update progress
            progress_bar.update(5)  # Now at 55%
            
            print("Extracting voice signatures for each segment...")
            
            # For very long files, limit the maximum number of segments
            if len(segment_boundaries) > 1000:
                print(f"Large number of segments detected ({len(segment_boundaries)}). Limiting to 1000 segments for performance.")
                # Keep boundaries at regular intervals
                indices = np.linspace(0, len(segment_boundaries)-2, 999, dtype=int)
                new_boundaries = [segment_boundaries[0]]  # Keep first boundary
                for idx in indices:
                    new_boundaries.append(segment_boundaries[idx+1])
                segment_boundaries = new_boundaries
                print(f"Reduced to {len(segment_boundaries)} segment boundaries.")
            
            # Extract comprehensive features for each segment for speaker identification
            segment_features = []
            valid_segments = []
            segment_durations = []
            
            # Track processing time for timeouts
            feature_extraction_start = time.time()
            timeout_duration = 300  # 5 minutes timeout for feature extraction
            
            # Calculate total segments for progress reporting
            total_segments = len(segment_boundaries) - 1
            print(f"Processing {total_segments} segments...")
            
            # Process segments with progress updates
            for i in range(total_segments):
                # Show progress for long segment lists
                if i % 10 == 0 or i == total_segments - 1:
                    print(f"  Processing segment {i+1}/{total_segments}...\r", end='')
                
                # Check for timeout
                if time.time() - feature_extraction_start > timeout_duration:
                    print(f"\n  WARNING: Feature extraction taking too long. Processed {i}/{total_segments} segments.")
                    print("  Proceeding with partial data to avoid hanging.")
                    break
                
                # Calculate segment duration
                segment_duration = segment_boundaries[i+1] - segment_boundaries[i]
                segment_durations.append(segment_duration)
                
                # Find frames that belong to this segment
                start_frame = int(segment_boundaries[i] / (step_size / sampling_rate))
                end_frame = int(segment_boundaries[i+1] / (step_size / sampling_rate))
                
                # Ensure we don't exceed array bounds
                start_frame = max(0, min(start_frame, len(energy_norm) - 1))
                end_frame = max(start_frame + 1, min(end_frame, len(energy_norm)))
                
                if end_frame > start_frame:
                    # Get segment frames
                    segment_frames = np.arange(start_frame, end_frame)
                    
                    # Skip if too few frames
                    if len(segment_frames) < 3:
                        segment_features.append(np.zeros(30))  # Default empty features
                        valid_segments.append(False)
                        continue
                    
                    # Extract all features for this segment
                    features, valid_pitch = extract_segment_features(
                        segment_frames, energy_norm, spectral_centroid_norm, 
                        spectral_rolloff_norm, zcr_norm, spectral_flux_norm, 
                        harmonicity_norm, mfcc_norm, segment_duration, 
                        f0_contour, segment_boundaries, i, sampling_rate
                    )
                    
                    segment_features.append(features)
                    valid_segments.append(True)
                else:
                    # Invalid segment
                    segment_features.append(np.zeros(30))  # Default empty features
                    valid_segments.append(False)
            
            print("\nVoice signature extraction complete.")
            
            # Update progress
            progress_bar.update(5)  # Now at 60%
            
            print("Identifying unique speaker characteristics...")
            
            # Convert to numpy array and handle any NaN values
            segment_features = np.array(segment_features)
            segment_features = np.nan_to_num(segment_features)
            valid_segments = np.array(valid_segments)
            
            # Perform enhanced speaker clustering
            speaker_labels = np.zeros(len(segment_features), dtype=int)
            
            if len(segment_features) > 0 and np.sum(valid_segments) >= num_speakers:
                try:
                    # Extract features for valid segments only
                    valid_features = segment_features[valid_segments]
                    
                    # Check that we have properly shaped features
                    if len(valid_features.shape) < 2 or valid_features.shape[0] < num_speakers or valid_features.shape[1] < 4:
                        raise ValueError(f"Not enough valid feature data: shape {valid_features.shape}")
                    
                    # Normalize features for clustering
                    from scipy import stats
                    
                    # First get feature weight vector - give more weight to MFCCs and pitch
                    feature_weights = np.ones(valid_features.shape[1])
                    feature_weights[3:5] = 2.0  # Pitch features (centroid mean and std)
                    feature_weights[10] = 0.2   # Less weight on duration
                    feature_weights[11:] = 1.5  # More weight on MFCC features (voice timbre)
                    
                    # Apply weights to features
                    weighted_features = valid_features * feature_weights
                    
                    # Use more robust clustering
                    from scipy.cluster.vq import kmeans, vq
                    from scipy.spatial.distance import cdist
                    
                    # Optimize k-means with multiple runs
                    best_distortion = float('inf')
                    best_centroids = None
                    best_labels = None
                    
                    # Run k-means multiple times with different initializations
                    for run in range(10):
                        centroids, distortion = kmeans(weighted_features, num_speakers, iter=50)
                        if distortion < best_distortion:
                            best_distortion = distortion
                            best_centroids = centroids
                            
                            # Get cluster assignments
                            best_labels, _ = vq(weighted_features, centroids)
                    
                    # Refine clustering further to improve speaker consistency
                    # Calculate distance of each point to all centroids
                    distances = cdist(weighted_features, best_centroids)
                    
                    # Assign ambiguous points (close to multiple clusters) to most common nearby cluster
                    for i in range(len(best_labels)):
                        # Find points where the difference between best and second-best cluster is small
                        sorted_distances = np.sort(distances[i])
                        if len(sorted_distances) > 1:
                            diff = sorted_distances[1] - sorted_distances[0]
                            
                            # If point is ambiguous (close to boundary)
                            if diff < 0.2 * np.mean(sorted_distances):
                                # Look at 2-frame window around this segment
                                window_indices = []
                                original_idx = np.where(valid_segments)[0][i]
                                
                                # Find nearby valid segments
                                for j in range(max(0, original_idx-2), min(original_idx+3, len(valid_segments))):
                                    if valid_segments[j] and j != original_idx:
                                        nearby_valid_idx = np.where(np.where(valid_segments)[0] == j)[0]
                                        if len(nearby_valid_idx) > 0:
                                            window_indices.append(nearby_valid_idx[0])
                                
                                # Count cluster labels in window
                                if window_indices:
                                    window_labels = best_labels[window_indices]
                                    # Most common label in window
                                    from collections import Counter
                                    most_common = Counter(window_labels).most_common(1)[0][0]
                                    best_labels[i] = most_common
                    
                    # Create full labels array
                    valid_indices = np.where(valid_segments)[0]
                    for i, idx in enumerate(valid_indices):
                        speaker_labels[idx] = best_labels[i]
                    
                    # Handle invalid segments by copying labels from nearby valid segments
                    for i in range(len(speaker_labels)):
                        if not valid_segments[i]:
                            # Find closest valid segment
                            closest_valid = min(valid_indices, key=lambda x: abs(x-i))
                            speaker_labels[i] = speaker_labels[closest_valid]
                    
                except Exception as e:
                    print(f"Advanced clustering failed: {e}, using simpler approach")
                    # Fall back to simpler approach
                    # Use pitch and energy to distinguish speakers
                    
                    # Get valid segments
                    valid_indices = np.where(valid_segments)[0]
                    valid_features = segment_features[valid_indices]
                    
                    # Check if we have enough valid data for the simpler approach
                    if len(valid_features) > 0:
                        # Make sure valid_features is properly shaped
                        if len(valid_features.shape) < 2:
                            # Reshape to 2D if it's 1D - this can happen with very few segments
                            print("Reshaping features for basic analysis")
                            
                            # Create basic 2D array with energy in first column
                            # and either use existing features or zeros as fallback
                            if valid_features.shape[0] > 0:
                                # Use energy as the main feature - typically first element in our feature vector
                                energy_values = valid_features
                                # Create a basic 2D array with this single feature
                                valid_features = np.column_stack((energy_values, np.zeros((len(energy_values), 3))))
                            else:
                                # Complete fallback with dummy data
                                valid_features = np.zeros((2, 4))
                                
                        # Try to use pitch (centroid_mean is at index 3) as primary feature if available
                        if valid_features.shape[1] > 3:
                        pitch_values = valid_features[:, 3]
                        else:
                            # Fallback to first column (energy) or any available feature
                            pitch_values = valid_features[:, 0]
                        
                        # Sort segments by pitch
                        sorted_indices = np.argsort(pitch_values)
                        
                        # Assign labels based on pitch - lower pitch is typically speaker 0, higher is speaker 1
                        # For two speakers, we can just split at the median
                        median_idx = len(sorted_indices) // 2
                        
                        temp_labels = np.zeros(len(sorted_indices), dtype=int)
                        temp_labels[sorted_indices[median_idx:]] = 1
                        
                        # Transfer labels to original indices
                        for i, idx in enumerate(valid_indices):
                            speaker_labels[idx] = temp_labels[i]
                        
                        # Handle invalid segments
                        for i in range(len(speaker_labels)):
                            if not valid_segments[i]:
                                # Find closest valid segment
                                closest_valid = min(valid_indices, key=lambda x: abs(x-i))
                                speaker_labels[closest_valid] = speaker_labels[i]
                    else:
                        # Fallback if everything else fails - alternate speakers
                        for i in range(len(speaker_labels)):
                            speaker_labels[i] = i % num_speakers
            else:
                # Not enough valid segments - use simple alternating approach
                for i in range(len(speaker_labels)):
                    speaker_labels[i] = i % num_speakers
                print("Warning: Not enough valid segments for accurate speaker identification")
            
            # Update progress
            progress_bar.update(15)  # Now at 75%
            
            print("Generating final speaker timeline...")
            
            # Create frame-level speaker assignments (10 frames per second)
            frame_rate = 10
            frame_count = int(duration * frame_rate)
            flags = np.zeros(frame_count, dtype=int)
            
            for i in range(len(segment_boundaries) - 1):
                if i < len(speaker_labels):
                    start_frame = int(segment_boundaries[i] * frame_rate)
                    end_frame = int(segment_boundaries[i+1] * frame_rate)
                    
                    # Ensure we don't exceed array bounds
                    start_frame = max(0, min(start_frame, frame_count - 1))
                    end_frame = max(start_frame + 1, min(end_frame, frame_count))
                    
                    flags[start_frame:end_frame] = speaker_labels[i]
            
            # Update progress
            progress_bar.update(5)  # Now at 80%
            
            # Apply smoothing to remove short segments
            print("Refining speaker transitions...")
            
            # Medium smoothing window (2 seconds) for analyzing typical segment length
            med_window = 20  # frames (2 seconds at 10fps)
            
            # Count segments and their durations
            segments_info = []
            current_speaker = flags[0]
            segment_start = 0
            
            for i in range(1, len(flags)):
                if flags[i] != current_speaker:
                    segments_info.append({
                        'speaker': current_speaker,
                        'start': segment_start,
                        'end': i,
                        'duration': i - segment_start
                    })
                    current_speaker = flags[i]
                    segment_start = i
            
            # Add the last segment
            if segment_start < len(flags):
                segments_info.append({
                    'speaker': current_speaker,
                    'start': segment_start,
                    'end': len(flags),
                    'duration': len(flags) - segment_start
                })
            
            # Calculate median segment duration
            if segments_info:
                durations = [s['duration'] for s in segments_info]
                median_duration = np.median(durations)
                
                # Set minimum segment length (reduced for even quicker exchanges)
                min_segment_length = max(1, min(int(median_duration * 0.15), 5))  # Greatly reduced threshold
                
                # Only smooth extremely short segments that are likely errors
                smoothed_flags = np.copy(flags)
                
                for segment in segments_info:
                    # Only process extremely short segments
                    if segment['duration'] <= 1:  # Only segments ≤ 0.1 seconds
                        # Find adjacent segments
                        segment_idx = segments_info.index(segment)
                        prev_speaker = segments_info[segment_idx-1]['speaker'] if segment_idx > 0 else None
                        next_speaker = segments_info[segment_idx+1]['speaker'] if segment_idx < len(segments_info)-1 else None
                        
                        # If surrounded by same speaker, merge with that speaker
                        if prev_speaker is not None and next_speaker is not None and prev_speaker == next_speaker:
                            smoothed_flags[segment['start']:segment['end']] = prev_speaker
                        # Check if part of rapid exchange pattern - preserve most alternating patterns
                        else:
                            # Look for alternating patterns
                            is_alternating_pattern = False
                            if segment_idx > 1 and segment_idx < len(segments_info)-2:
                                # Check for ABABAB pattern
                                if (segments_info[segment_idx-2]['speaker'] == next_speaker or 
                                    segments_info[segment_idx+2]['speaker'] == prev_speaker):
                                    is_alternating_pattern = True
                            
                            # Preserve alternating patterns as they're likely real
                            if is_alternating_pattern:
                                # No change - preserve the alternating pattern
                                pass
                        elif prev_speaker is not None and next_speaker is not None:
                                # Merge with adjacent segment with more similar features
                            prev_duration = segments_info[segment_idx-1]['duration']
                            next_duration = segments_info[segment_idx+1]['duration']
                                
                                # Simple heuristic: merge with longer segment
                            if prev_duration > next_duration:
                                smoothed_flags[segment['start']:segment['end']] = prev_speaker
                            else:
                                smoothed_flags[segment['start']:segment['end']] = next_speaker
                
                flags = smoothed_flags
            
            # Update progress
            progress_bar.update(10)  # Now at 90%
            
            # Get final segment information
            print("Creating final segment list...")
            segments = []
            if len(flags) > 0:
                current_speaker = flags[0]
                start_time = 0
                
                for i in range(1, len(flags)):
                    # Convert frame index to time
                    time_sec = i * 0.1  # 100ms segments
                    
                    if flags[i] != current_speaker:
                        # Speaker changed, add segment
                        end_time = time_sec
                        segment = {
                            "speaker": int(current_speaker),
                            "start": round(start_time, 2),
                            "end": round(end_time, 2),
                            "duration": round(end_time - start_time, 2)
                        }
                        segments.append(segment)
                        
                        # Reset for new segment
                        current_speaker = flags[i]
                        start_time = time_sec
                
                # Add the last segment
                segment = {
                    "speaker": int(current_speaker),
                    "start": round(start_time, 2),
                    "end": round(len(flags) * 0.1, 2),
                    "duration": round((len(flags) * 0.1) - start_time, 2)
                }
                segments.append(segment)
            
            # Complete the progress bar
            progress_bar.update(10)  # Now at 100%
            progress_bar.close()
            
            # Calculate processing times for different stages
            total_processing_time = time.time() - global_start_time
            
            # Print time report in a more human-readable format
            print("\nDiarization Performance Summary:")
            print("-------------------------------")
            if duration > 0:
                print(f"Real-time factor: {total_processing_time / duration:.2f}x ({total_processing_time:.2f} seconds processing for {duration:.2f} seconds audio)")
            else:
                print(f"Total processing time: {total_processing_time:.2f} seconds")
            
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
                
                print(f"Segment {i+1}: Speaker {speaker} - {segment['start']}s to {segment['end']}s (Duration: {duration}s)")
            
            # Print speaker statistics
            print("\nSpeaker Statistics:")
            print("------------------")
            for speaker, duration in speaker_durations.items():
                percentage = (duration / total_duration) * 100
                print(f"Speaker {speaker}: {duration:.2f}s ({percentage:.2f}%)")
            
            # Plot results if requested
            if plot:
                plot_diarization(flags, num_speakers, audio_path)
            
            return segments
        else:
            print("Error: No audio features extracted")
            return None
    
    except Exception as e:
        print(f"Error performing diarization: {e}")
        import traceback
        traceback.print_exc()
        return None

def plot_diarization(flags, num_speakers, audio_path):
    """Plot the diarization results."""
    try:
        print("Generating diarization plot...")
        plt.figure(figsize=(15, 4))
        timeline = np.arange(len(flags)) * 0.1  # 100ms segments
        plt.plot(timeline, flags)
        plt.yticks(np.arange(num_speakers), [f"Speaker {i}" for i in range(num_speakers)])
        plt.xlabel("Time (seconds)")
        plt.ylabel("Speaker")
        plt.title(f"Speaker Diarization for {os.path.basename(audio_path)}")
        plt.grid(True)
        
        # Save plot
        plot_path = os.path.splitext(audio_path)[0] + "_diarization.png"
        plt.savefig(plot_path)
        print(f"Diarization plot saved to {plot_path}")
        plt.show()
    except Exception as e:
        print(f"Error plotting diarization results: {e}")

def save_diarization_to_file(segments, audio_path):
    """Save diarization results to a text file."""
    output_path = os.path.splitext(audio_path)[0] + "_diarization.txt"
    try:
        print("Saving diarization results to file...")
        with open(output_path, 'w') as file:
            file.write("Speaker Diarization Results\n")
            file.write("=========================\n\n")
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
                
                file.write(f"Segment {i+1}: Speaker {speaker} - {segment['start']}s to {segment['end']}s (Duration: {duration}s)\n")
            
            # Write speaker statistics
            file.write("\nSpeaker Statistics:\n")
            file.write("------------------\n")
            for speaker, duration in speaker_durations.items():
                percentage = (duration / total_duration) * 100
                file.write(f"Speaker {speaker}: {duration:.2f}s ({percentage:.2f}%)\n")
        
        print(f"Diarization results saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving diarization results: {e}")
        return None

def perform_chunked_diarization(audio_path, num_speakers=2, plot=True, fast_mode=False, chunk_size_minutes=3):
    """
    Perform high-precision diarization by processing audio in smaller chunks.
    
    Args:
        audio_path: Path to audio file
        num_speakers: Number of speakers to identify
        plot: Whether to plot results
        fast_mode: Whether to use fast processing (not recommended for best accuracy)
        chunk_size_minutes: Size of each processing chunk in minutes
        
    Returns:
        List of speaker segments
    """
    try:
        import time
        import librosa
        import numpy as np
        
        # Start time tracking for the entire process
        global_start_time = time.time()
        
        # Load audio file
        print("Loading audio file...")
        sampling_rate, signal = aIO.read_audio_file(audio_path)
        
        # Convert stereo to mono if needed
        if len(signal.shape) > 1 and signal.shape[1] > 1:
            signal = np.mean(signal, axis=1)
        
        # Calculate duration
        duration = len(signal) / float(sampling_rate)
        print(f"Audio duration: {duration:.2f} seconds")
        
        # Skip initial portion of the audio based on length
        skip_seconds = 60 if duration > 1200 else 30  # 1 minute for >20min videos, 30sec for shorter
        skip_samples = int(skip_seconds * sampling_rate)
        
        if skip_samples > 0 and skip_samples < len(signal):
            print(f"Skipping first {skip_seconds} seconds of audio")
            signal = signal[skip_samples:]
            duration = len(signal) / float(sampling_rate)
            
            # We'll add this offset back to all timestamps later
            time_offset = skip_seconds
        else:
            time_offset = 0
        
        # For very short files, just use normal diarization but with same settings
        if duration < chunk_size_minutes * 60:
            print(f"Processing as single chunk...")
            # Still use high-quality settings regardless of file length
            segments = perform_diarization(audio_path, num_speakers, plot, fast_mode=False)
            
            # Apply time offset to segments
            if time_offset > 0 and segments:
                for segment in segments:
                    segment['start'] += time_offset
                    segment['end'] += time_offset
            
            return segments
        
        # Calculate chunk size in samples
        chunk_size_samples = int(chunk_size_minutes * 60 * sampling_rate)
        
        # Calculate number of chunks with 50% overlap for better continuity
        overlap_ratio = 0.5
        step_size_samples = int(chunk_size_samples * (1 - overlap_ratio))
        num_chunks = max(1, int((len(signal) - chunk_size_samples) / step_size_samples) + 1)
        
        print(f"Processing audio in {num_chunks} overlapping chunks...")
        
        # Create temporary directory for chunk files
        import tempfile
        import os
        import shutil
        temp_dir = tempfile.mkdtemp()
        
        # Create intermediate results directory for chunk outputs
        intermediate_dir = os.path.join(os.path.dirname(audio_path), "intermediate_results")
        os.makedirs(intermediate_dir, exist_ok=True)
        
        try:
            # Split audio into chunks and process each
            chunk_segments = []
            all_segments_so_far = []
            
            for i in range(num_chunks):
                # Calculate chunk start and end
                start_sample = i * step_size_samples
                end_sample = min(start_sample + chunk_size_samples, len(signal))
                
                # Take the chunk
                chunk_signal = signal[start_sample:end_sample]
                
                # Calculate chunk start time in seconds
                chunk_start_time = start_sample / sampling_rate
                chunk_end_time = end_sample / sampling_rate
                
                # Create temp file for chunk
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.wav")
                
                # Save chunk to file
                import soundfile as sf
                sf.write(chunk_path, chunk_signal, sampling_rate)
                
                # Process chunk with high precision
                print(f"\n--- Processing chunk {i+1}/{num_chunks} ({chunk_start_time+time_offset:.1f}s to {chunk_end_time+time_offset:.1f}s) ---")
                
                # Reduce verbosity during chunk processing
                old_stdout = sys.stdout
                try:
                    # Redirect stdout to suppress most messages
                    null_output = open(os.devnull, 'w')
                    sys.stdout = null_output
                    
                    # Process with highest precision (never use fast mode for chunks)
                    chunk_result = perform_diarization(chunk_path, num_speakers, plot=False, fast_mode=False)
                finally:
                    # Restore stdout
                    sys.stdout = old_stdout
                
                if chunk_result:
                    # Adjust segment times based on chunk start time and global offset
                    for segment in chunk_result:
                        segment['start'] += chunk_start_time + time_offset
                        segment['end'] += chunk_start_time + time_offset
                        segment['chunk'] = i
                    
                    chunk_segments.append(chunk_result)
                    
                    # Print chunk results chronologically
                    print(f"\n*** CHUNK {i+1}/{num_chunks} COMPLETED ***")
                    print(f"Time range: {chunk_start_time+time_offset:.2f}s - {chunk_end_time+time_offset:.2f}s")
                    print(f"Found {len(chunk_result)} segments")
                    print_segment_summary(chunk_result)
                    
                    # Update and save partial results
                    all_segments_so_far.extend(chunk_result)
                    all_segments_so_far.sort(key=lambda x: x['start'])  # Keep everything chronological
                    
                    # Save intermediate results showing all processed segments so far
                    print("\nAll processed segments so far:")
                    print("-----------------------------")
                    print_segment_summary(all_segments_so_far)
                    
                    # Save to file
                    partial_output_path = os.path.join(intermediate_dir, "partial_results.txt")
                    save_diarization_to_file(all_segments_so_far, partial_output_path)
                    print(f"\nProcessed {len(all_segments_so_far)} total segments")
                    
                    # Show progress
                    progress_pct = (i + 1) / num_chunks * 100
                    elapsed = time.time() - global_start_time
                    estimated_total = elapsed / (i + 1) * num_chunks
                    remaining = max(0, estimated_total - elapsed)
                    print(f"Progress: {progress_pct:.1f}% complete. Est. remaining: {remaining/60:.1f} minutes\n")
                
                else:
                    print(f"Warning: Chunk {i+1} processing failed")
                
                # Report progress percentage
                progress_pct = (i + 1) / num_chunks * 100
                elapsed = time.time() - global_start_time
                estimated_total = elapsed / (i + 1) * num_chunks
                remaining = max(0, estimated_total - elapsed)
                print(f"Progress: {progress_pct:.1f}% complete. Est. remaining: {remaining/60:.1f} minutes")
            
            # Merge all chunks and resolve speaker identities across chunks
            if not chunk_segments:
                print("Error: No valid segments found")
                return None
            
            print("\nMerging chunks and resolving speaker identities...")
            merged_segments = stitch_segments(chunk_segments, num_speakers)
            
            # Final smoothing to remove artifacts from chunk boundaries
            smoothed_segments = smooth_boundary_artifacts(merged_segments, overlap_ratio * chunk_size_minutes * 60)
            
            # Plot final results if requested
            if plot:
                # Add the time offset back to the full duration for plotting
                full_duration = duration + time_offset
                plot_diarization_from_segments(smoothed_segments, num_speakers, full_duration, audio_path)
            
            # Calculate total processing time
            total_processing_time = time.time() - global_start_time
            
            # Print performance summary
            print("\n*** DIARIZATION COMPLETE ***")
            print(f"Total segments: {len(smoothed_segments)}")
            
            # Save results to file
            output_path = os.path.splitext(audio_path)[0] + "_diarization.txt"
            save_diarization_to_file(smoothed_segments, output_path)
            
            print(f"Final results saved to {output_path}")
            
            return smoothed_segments
            
        finally:
            # Clean up temp files but keep intermediate results
            shutil.rmtree(temp_dir)
    
    except Exception as e:
        print(f"Error in chunked diarization: {e}")
        import traceback
        traceback.print_exc()
        return None

def print_segment_summary(segments):
    """Print a summary of the segments for a chunk."""
    # Sort segments chronologically by start time
    sorted_segments = sorted(segments, key=lambda x: x['start'])
    
    # Print all segments chronologically
    print("\nSegments in chronological order:")
    print("--------------------------------")
    for i, segment in enumerate(sorted_segments):
        print(f"Segment {i+1}: Speaker {segment['speaker']} - {segment['start']:.2f}s to {segment['end']:.2f}s (Duration: {segment['duration']:.2f}s)")
    
    # Calculate and print statistics after the chronological listing
    print("\nSpeaker Statistics:")
    print("------------------")
    total_duration = sum(segment['duration'] for segment in segments)
    speaker_durations = {}
    
    for segment in segments:
        speaker = segment['speaker']
        duration = segment['duration']
        
        if speaker not in speaker_durations:
            speaker_durations[speaker] = 0
        speaker_durations[speaker] += duration
    
    # Print speaker statistics
    for speaker, duration in speaker_durations.items():
        percentage = (duration / total_duration) * 100 if total_duration > 0 else 0
        print(f"Speaker {speaker}: {duration:.2f}s ({percentage:.1f}%)")

def stitch_segments(chunk_segments, num_speakers):
    """
    Stitch together segments from different chunks and resolve speaker identities.
    
    Args:
        chunk_segments: List of segment lists from each chunk
        num_speakers: Number of speakers
        
    Returns:
        List of merged segments with consistent speaker IDs
    """
    if not chunk_segments:
        return []
    
    # Flatten all segments from all chunks
    all_segments = [seg for chunk in chunk_segments for seg in chunk]
    
    if not all_segments:
        return []
    
    # Sort segments by start time
    all_segments.sort(key=lambda x: x['start'])
    
    # For segments that overlap significantly (from chunk overlap), keep the one from the earlier chunk
    # as it's processed with more context from that chunk
    filtered_segments = []
    for i, segment in enumerate(all_segments):
        # Skip segments already marked for removal
        if segment.get('remove', False):
            continue
            
        # Add segment to filtered list
        filtered_segments.append(segment)
        
        # Mark overlapping segments from later chunks for removal
        for j in range(i+1, len(all_segments)):
            other = all_segments[j]
            if other.get('remove', False):
                continue
                
            # Calculate overlap
            overlap_start = max(segment['start'], other['start'])
            overlap_end = min(segment['end'], other['end'])
            overlap_duration = max(0, overlap_end - overlap_start)
            
            # If segments overlap significantly (>50% of either segment)
            if (overlap_duration > 0.5 * segment['duration'] or 
                overlap_duration > 0.5 * other['duration']):
                # If from different chunks, keep segment from earlier chunk (lower chunk number)
                if 'chunk' in segment and 'chunk' in other and segment['chunk'] < other['chunk']:
                    other['remove'] = True
    
    # Filter out segments marked for removal
    filtered_segments = [s for s in filtered_segments if not s.get('remove', False)]
    
    # Now resolve speaker identity continuity across chunks
    if num_speakers == 2:  # For binary case, use simple speaker mapping based on pitch
        resolve_two_speaker_identities(filtered_segments)
    else:
        # For more speakers, use more complex resolution
        resolve_multi_speaker_identities(filtered_segments, num_speakers)
    
    return filtered_segments

def resolve_two_speaker_identities(segments):
    """
    Resolve speaker identities for the two-speaker case by using voice characteristics.
    This will rewrite speaker IDs to ensure consistency.
    """
    if not segments:
        return
    
    # Split segments by speaker ID from original assignments
    speakers = {}
    for segment in segments:
        spk = segment['speaker']
        if spk not in speakers:
            speakers[spk] = []
        speakers[spk].append(segment)
    
    # If only one speaker found, nothing to resolve
    if len(speakers) <= 1:
        return
    
    # Calculate average estimated pitch/energy for each speaker
    # We'll use the 'centroid_mean' if available, otherwise just use chunk assignment
    speaker_characteristics = {}
    for spk, spk_segments in speakers.items():
        # If segments have 'centroid_mean' (or any voice characteristic), use that
        if any('centroid_mean' in seg for seg in spk_segments):
            mean_values = [seg.get('centroid_mean', 0) for seg in spk_segments if 'centroid_mean' in seg]
            speaker_characteristics[spk] = sum(mean_values) / len(mean_values) if mean_values else 0
        else:
            # Just use segment durations as a fallback heuristic
            speaker_characteristics[spk] = sum(seg['duration'] for seg in spk_segments)
    
    # Reassign speakers consistently - typically lower voice/longer speaking time gets ID 0
    sorted_speakers = sorted(speaker_characteristics.items(), key=lambda x: x[1])
    speaker_mapping = {spk: i for i, (spk, _) in enumerate(sorted_speakers)}
    
    # Apply mapping to all segments
    for segment in segments:
        segment['speaker'] = speaker_mapping[segment['speaker']]

def resolve_multi_speaker_identities(segments, num_speakers):
    """
    Resolve speaker identities for the multi-speaker case.
    Uses voice characteristics and temporal proximity to match speakers across chunks.
    """
    # For now, use the same approach as two-speaker case
    # In a more advanced version, we could build speaker profiles based on MFCCs, etc.
    resolve_two_speaker_identities(segments)

def smooth_boundary_artifacts(segments, overlap_duration):
    """
    Smooth artifacts that might occur at chunk boundaries.
    
    Args:
        segments: List of speaker segments
        overlap_duration: Duration of chunk overlap in seconds
        
    Returns:
        Smoothed segments
    """
    if not segments:
        return []
    
    # Sort segments by start time
    segments.sort(key=lambda x: x['start'])
    
    # Merge very close segments from the same speaker 
    # (these might be artifacts from chunk boundaries)
    merged_segments = []
    for segment in segments:
        if not merged_segments:
            merged_segments.append(segment.copy())
            continue
        
        prev_segment = merged_segments[-1]
        
        # If same speaker and gap is small (within 0.5 second)
        if (segment['speaker'] == prev_segment['speaker'] and 
            segment['start'] - prev_segment['end'] < 0.5):
            # Merge with previous segment
            prev_segment['end'] = segment['end']
            prev_segment['duration'] = prev_segment['end'] - prev_segment['start']
        else:
            merged_segments.append(segment.copy())
    
    # Smooth out very short segments (< 0.3 seconds) that might be artifacts
    smoothed_segments = []
    min_valid_duration = 0.3  # minimum valid segment duration in seconds
    
    for i, segment in enumerate(merged_segments):
        # Keep segments longer than minimum duration
        if segment['duration'] >= min_valid_duration:
            smoothed_segments.append(segment)
            continue
            
        # For very short segments, check neighbors
        prev_speaker = merged_segments[i-1]['speaker'] if i > 0 else None
        next_speaker = merged_segments[i+1]['speaker'] if i < len(merged_segments)-1 else None
        
        # If surrounded by same speaker, merge with that speaker
        if prev_speaker is not None and next_speaker is not None and prev_speaker == next_speaker:
            # Skip this segment (will be merged by adjusting prev/next)
            if smoothed_segments and smoothed_segments[-1]['speaker'] == prev_speaker:
                # Extend previous segment end time
                smoothed_segments[-1]['end'] = merged_segments[i+1]['end']
                smoothed_segments[-1]['duration'] = smoothed_segments[-1]['end'] - smoothed_segments[-1]['start']
                # Skip next segment too as it's now merged
                i += 1
        else:
            # Keep the segment otherwise
            smoothed_segments.append(segment)
    
    return smoothed_segments

def plot_diarization_from_segments(segments, num_speakers, duration, audio_path):
    """Plot diarization results from segment list."""
    try:
        print("Generating diarization plot...")
        plt.figure(figsize=(15, 4))
        
        # Convert segments to timeline
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
        plot_path = os.path.splitext(audio_path)[0] + "_diarization.png"
        plt.savefig(plot_path)
        print(f"Diarization plot saved to {plot_path}")
        plt.close()  # Close the figure to avoid displaying it inline
    except Exception as e:
        print(f"Error plotting diarization results: {e}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Speaker Diarization using pyAudioAnalysis")
    parser.add_argument("input_file", nargs="?", help="Path to input audio or video file (positional argument)")
    parser.add_argument("-i", "--input", help="Path to input audio or video file")
    parser.add_argument("-s", "--speakers", type=int, default=2, help="Number of speakers (default: 2)")
    parser.add_argument("-p", "--plot", action="store_true", help="Plot diarization results")
    parser.add_argument("-o", "--output", help="Output directory (default: same as input)")
    parser.add_argument("-f", "--fast", action="store_true", help="Use fast mode for quicker processing (NOT recommended for best accuracy)")
    parser.add_argument("-c", "--chunked", action="store_true", help="Process audio in chunks for better accuracy on long files")
    parser.add_argument("--chunk-size", type=int, default=3, help="Size of processing chunks in minutes (default: 3)")
    parser.add_argument("--timeout", type=int, default=7200, help="Timeout in seconds (default: 2 hours)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Reduce output verbosity")
    
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
    
    # Suppress verbose output if quiet mode
    if args.quiet:
        old_stdout = sys.stdout
        null_output = open(os.devnull, 'w')
        
    # Apply global timeout to avoid hanging indefinitely
    import signal
    
    def timeout_handler(signum, frame):
        print("\n\nTimeout reached. The process is taking too long and will be terminated.")
        sys.exit(1)
    
    # Set the timeout handler - increase default timeout to 2 hours
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(args.timeout)  # Default 2 hour timeout
    
    try:
    # Set output directory
    output_dir = args.output if args.output else os.path.dirname(input_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Process input file
    file_extension = os.path.splitext(input_file)[1].lower()
    audio_path = input_file
    
    # If input is a video file, extract audio
    if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.flv']:
            print("Extracting audio from video...")
        output_audio_path = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + ".wav")
            
            # Redirect stdout during audio extraction if quiet mode
            if args.quiet:
                sys.stdout = null_output
                
        audio_path = extract_audio_from_video(input_file, output_audio_path)
            
            # Restore stdout if quiet mode
            if args.quiet:
                sys.stdout = old_stdout
                
        if not audio_path:
            return
    
            print("Audio extraction complete")
        
        # Perform diarization, using chunked mode for better accuracy if requested
        if args.chunked:
            print(f"Starting chunked diarization...")
            
            # Redirect stdout during processing if quiet mode
            if args.quiet:
                sys.stdout = null_output
                
            segments = perform_chunked_diarization(
                audio_path, 
                args.speakers, 
                args.plot, 
                args.fast,
                chunk_size_minutes=args.chunk_size
            )
            
            # Restore stdout if quiet mode
            if args.quiet:
                sys.stdout = old_stdout
        else:
            print("Starting diarization...")
            
            # Redirect stdout during processing if quiet mode
            if args.quiet:
                sys.stdout = null_output
                
            segments = perform_diarization(
                audio_path, 
                args.speakers, 
                args.plot, 
                fast_mode=args.fast
            )
            
            # Restore stdout if quiet mode
            if args.quiet:
                sys.stdout = old_stdout
    
    # Save results to file
    if segments:
            output_path = save_diarization_to_file(segments, audio_path)
            print(f"\nDiarization complete. Results saved to {output_path}")
            
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
        
        # Cancel the alarm when done
        signal.alarm(0)
    
    except Exception as e:
        # Restore stdout if quiet mode
        if args.quiet:
            sys.stdout = old_stdout
            
        print(f"\nError during processing: {e}")
        # Cancel the alarm
        signal.alarm(0)
        import traceback
        traceback.print_exc()
        return
    finally:
        # Make sure stdout is restored
        if args.quiet:
            sys.stdout = old_stdout

if __name__ == "__main__":
    main()


