import numpy as np
import librosa
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import os
import datetime
import logging

class ScoringSystem:
    def __init__(self):
        self.baseline_hr = 80  # Default baseline HR, can be adjusted
        self.hr_threshold = 10  # Default threshold for HR spikes
        
    def calculate_verbal_engagement(self, diarization_data: List[Dict]) -> float:
        """Calculate verbal engagement score based on turn balance"""
        speaker_times = {}
        
        for segment in diarization_data:
            speaker = segment.get('speaker', 'unknown')
            duration = segment.get('end', 0) - segment.get('start', 0)
            speaker_times[speaker] = speaker_times.get(speaker, 0) + duration
        
        if len(speaker_times) < 2:
            return 0.0
            
        # Get the two speakers with most speaking time
        top_speakers = sorted(speaker_times.items(), key=lambda x: x[1], reverse=True)[:2]
        speaker1_time, speaker2_time = top_speakers[0][1], top_speakers[1][1]
        
        # Calculate engagement score
        engagement_score = 1 - abs(speaker1_time - speaker2_time) / (speaker1_time + speaker2_time)
        return max(0.0, min(1.0, engagement_score))
    
    def calculate_hr_metrics(self, hr_data: List[Dict]) -> Dict:
        """Calculate various heart rate metrics"""
        if not hr_data:
            return {
                'avg_hr': 0,
                'hr_variability': 0,
                'spike_count': 0,
                'recovery_time': 0
            }
            
        hr_values = [point['hr'] for point in hr_data]
        timestamps = [point['timestamp'] for point in hr_data]
        
        # Calculate average HR
        avg_hr = sum(hr_values) / len(hr_values)
        
        # Calculate HR variability
        hr_var = np.std(hr_values)
        
        # Calculate spike count
        spike_count = sum(1 for hr in hr_values if hr > self.baseline_hr + self.hr_threshold)
        
        # Calculate recovery time
        recovery_time = 0
        in_spike = False
        last_spike_time = 0
        
        for i, (hr, timestamp) in enumerate(zip(hr_values, timestamps)):
            if hr > self.baseline_hr + self.hr_threshold:
                if not in_spike:
                    in_spike = True
                    last_spike_time = timestamp
            elif in_spike:
                in_spike = False
                recovery_time = max(recovery_time, timestamp - last_spike_time)
        
        return {
            'avg_hr': avg_hr,
            'hr_variability': hr_var,
            'spike_count': spike_count,
            'recovery_time': recovery_time
        }
    
    def calculate_pitch_range(self, audio_path: str, diarization_data: List[Dict]) -> Dict[str, float]:
        """Calculate pitch range for each speaker"""
        try:
            # Load audio file
            y, sr = librosa.load(audio_path)
            
            # Calculate pitch for the entire audio
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            
            speaker_pitch_ranges = {}
            
            for segment in diarization_data:
                speaker = segment.get('speaker', 'unknown')
                start_frame = int(segment['start'] * sr)
                end_frame = int(segment['end'] * sr)
                
                # Extract pitch values for this segment
                segment_pitches = pitches[:, start_frame:end_frame]
                valid_pitches = segment_pitches[segment_pitches > 0]
                
                if len(valid_pitches) > 0:
                    pitch_range = np.max(valid_pitches) - np.min(valid_pitches)
                    speaker_pitch_ranges[speaker] = speaker_pitch_ranges.get(speaker, []) + [pitch_range]
            
            # Calculate average pitch range per speaker
            return {speaker: np.mean(ranges) for speaker, ranges in speaker_pitch_ranges.items()}
            
        except Exception as e:
            print(f"Error calculating pitch range: {e}")
            return {}
    
    def calculate_speech_rate(self, diarization_data: List[Dict]) -> Dict[str, float]:
        """Calculate speech rate (words per minute) for each speaker"""
        speaker_rates = {}
        
        for segment in diarization_data:
            speaker = segment.get('speaker', 'unknown')
            duration = segment.get('end', 0) - segment.get('start', 0)
            text = segment.get('text', '')
            
            # Count words in text
            word_count = len(text.split())
            
            # Calculate words per minute
            if duration > 0:
                words_per_minute = (word_count / duration) * 60
                speaker_rates[speaker] = speaker_rates.get(speaker, []) + [words_per_minute]
        
        # Calculate average speech rate per speaker
        return {speaker: np.mean(rates) for speaker, rates in speaker_rates.items()}
    
    def calculate_silence_metrics(self, diarization_data: List[Dict]) -> Dict:
        """Calculate silence-related metrics"""
        if not diarization_data:
            return {
                'total_silence': 0,
                'silence_ratio': 0,
                'avg_silence': 0
            }
        
        # Sort segments by start time
        sorted_segments = sorted(diarization_data, key=lambda x: x['start'])
        
        # Calculate silence durations between segments
        silences = []
        for i in range(len(sorted_segments) - 1):
            silence_duration = sorted_segments[i + 1]['start'] - sorted_segments[i]['end']
            if silence_duration > 0:
                silences.append(silence_duration)
        
        total_duration = sorted_segments[-1]['end'] - sorted_segments[0]['start']
        total_silence = sum(silences)
        
        return {
            'total_silence': total_silence,
            'silence_ratio': total_silence / total_duration if total_duration > 0 else 0,
            'avg_silence': np.mean(silences) if silences else 0
        }
    
    def calculate_all_scores(self, guid: str, audio_path: str, diarization_data: List[Dict], heart_rate_data: Optional[List[Dict]] = None) -> Dict:
        """Calculate all scores and return them in a format suitable for the UI"""
        try:
            # Validate inputs
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            if not diarization_data:
                logging.warning(f"No diarization data available for {guid}")
                diarization_data = []
            
            # Calculate all metrics
            heart_rate_metrics = self.calculate_hr_metrics(heart_rate_data) if heart_rate_data else None
            verbal_metrics = self.calculate_verbal_engagement(diarization_data)
            pitch_ranges = self.calculate_pitch_range(audio_path, diarization_data)
            speech_rates = self.calculate_speech_rate(diarization_data)
            silence_metrics = self.calculate_silence_metrics(diarization_data)
            
            # Format scores for UI with better normalization
            scores = {
                'turn_balance': {
                    'current': int(verbal_metrics * 100),
                    'original': int(verbal_metrics * 100),
                    'label': 'Turn Balance',
                    'description': 'Measures the balance of speaking time between participants'
                },
                'heart_rate_stability': {
                    'current': int((1 - min(heart_rate_metrics['hr_variability'] / 20, 1)) * 100) if heart_rate_metrics else 0,
                    'original': int((1 - min(heart_rate_metrics['hr_variability'] / 20, 1)) * 100) if heart_rate_metrics else 0,
                    'label': 'Heart Rate Stability',
                    'description': 'Measures the consistency of heart rate during the session'
                },
                'pitch_variation': {
                    'current': int((1 - min(max(pitch_ranges.values()) / 500, 1)) * 100) if pitch_ranges else 50,
                    'original': int((1 - min(max(pitch_ranges.values()) / 500, 1)) * 100) if pitch_ranges else 50,
                    'label': 'Pitch Variation',
                    'description': 'Measures the natural variation in voice pitch'
                },
                'speech_rate_consistency': {
                    'current': int((1 - min(max(speech_rates.values()) / 300, 1)) * 100) if speech_rates else 50,
                    'original': int((1 - min(max(speech_rates.values()) / 300, 1)) * 100) if speech_rates else 50,
                    'label': 'Speech Rate Consistency',
                    'description': 'Measures the consistency of speaking pace'
                },
                'silence_ratio': {
                    'current': int((1 - silence_metrics['silence_ratio']) * 100),
                    'original': int((1 - silence_metrics['silence_ratio']) * 100),
                    'label': 'Silence Ratio',
                    'description': 'Measures the appropriate use of pauses and silence'
                },
                'engagement': {
                    'current': int(verbal_metrics * 100),
                    'original': int(verbal_metrics * 100),
                    'label': 'Engagement',
                    'description': 'Measures overall participant engagement'
                },
                'clarity': {
                    'current': int((1 - min(silence_metrics['silence_ratio'], 0.5)) * 100),
                    'original': int((1 - min(silence_metrics['silence_ratio'], 0.5)) * 100),
                    'label': 'Clarity',
                    'description': 'Measures the clarity of communication'
                }
            }
            
            # Include detailed metrics for UI display with better formatting
            detailed_metrics = {
                'heart_rate_metrics': {
                    'current': heart_rate_metrics if heart_rate_metrics else {},
                    'original': heart_rate_metrics if heart_rate_metrics else {},
                    'label': 'Heart Rate Analysis',
                    'description': 'Detailed heart rate measurements and analysis'
                },
                'pitch_ranges': {
                    'current': pitch_ranges,
                    'original': pitch_ranges,
                    'label': 'Pitch Analysis',
                    'description': 'Detailed voice pitch measurements by speaker'
                },
                'speech_rates': {
                    'current': speech_rates,
                    'original': speech_rates,
                    'label': 'Speech Rate Analysis',
                    'description': 'Detailed speech rate measurements by speaker'
                },
                'silence_metrics': {
                    'current': silence_metrics,
                    'original': silence_metrics,
                    'label': 'Silence Analysis',
                    'description': 'Detailed analysis of pauses and silence'
                }
            }
            
            return {
                'success': True,
                'data': {
                    'scores': scores,
                    'detailed_metrics': detailed_metrics,
                    'timestamp': str(datetime.datetime.now())
                }
            }
        except Exception as e:
            logging.error(f"Error calculating scores: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_scores(self, guid: str, scores: Dict):
        """Save scores to a JSON file"""
        scores_dir = os.path.join('static', 'uploaded_videos', 'scores')
        os.makedirs(scores_dir, exist_ok=True)
        
        scores_file = os.path.join(scores_dir, f"{guid}_scores.json")
        with open(scores_file, 'w') as f:
            json.dump(scores, f, indent=2) 