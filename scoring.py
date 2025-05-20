import numpy as np
import librosa
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
import os
import datetime
import logging
from transformers import pipeline
import torch

# Helper function to convert NumPy types to standard Python types
def convert_numpy_types_to_python(data):
    if isinstance(data, dict):
        return {k: convert_numpy_types_to_python(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_types_to_python(i) for i in data]
    elif isinstance(data, (np.float32, np.float64, np.floating)): # Added np.floating for broader float coverage
        return float(data)
    elif isinstance(data, (np.int32, np.int64, np.integer)): # Added np.integer for broader int coverage
        return int(data)
    elif isinstance(data, np.ndarray):
        return convert_numpy_types_to_python(data.tolist())
    elif isinstance(data, np.bool_):
        return bool(data)
    return data

class ScoringSystem:
    def __init__(self):
        self.baseline_hr = 80  # Default baseline HR, can be adjusted
        self.hr_threshold = 10  # Default threshold for HR spikes
        
        # Determine device for sentiment analysis pipeline
        device_to_try = "cpu" # Default to CPU
        if torch.cuda.is_available():
            device_to_try = 0  # Use the first CUDA device (index)
            logging.info("CUDA device found. Attempting to use GPU for sentiment analysis.")
        elif torch.backends.mps.is_available(): # Check for MPS (Apple Silicon)
            device_to_try = "mps"
            logging.info("MPS device found. Attempting to use GPU (MPS) for sentiment analysis.")
        else:
            logging.info("No CUDA or MPS device found. Using CPU for sentiment analysis.")

        # Initialize sentiment analysis pipeline
        try:
            self.sentiment_classifier = pipeline(
                "text-classification",
                model='bhadresh-savani/roberta-base-emotion',
                return_all_scores=True,
                device=device_to_try 
            )
            logging.info(f"Sentiment analysis model loaded successfully on device: {device_to_try}")
        except Exception as e:
            logging.error(f"Failed to load sentiment analysis model on device '{device_to_try}': {e}")
            if device_to_try != "cpu":
                logging.info("Attempting to load sentiment model on CPU as fallback.")
                try:
                    self.sentiment_classifier = pipeline(
                        "text-classification",
                        model='bhadresh-savani/roberta-base-emotion',
                        return_all_scores=True,
                        device="cpu" 
                    )
                    logging.info("Sentiment analysis model loaded successfully on CPU (fallback).")
                except Exception as e_cpu:
                    logging.error(f"Failed to load sentiment analysis model on CPU as fallback: {e_cpu}")
                    self.sentiment_classifier = None
            else:
                self.sentiment_classifier = None # Already tried CPU
        
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
    
    def calculate_hr_metrics(self, hr_data: List[Dict], total_duration: Optional[float] = None) -> Dict:
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
    
    def calculate_speech_rate(self, diarization_data: List[Dict], total_duration: Optional[float] = None) -> Dict[str, float]:
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
    
    def calculate_silence_metrics(self, diarization_data: List[Dict], total_duration: Optional[float] = None) -> Dict:
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
    
    def analyze_sentiment_for_speakers(self, diarization_data: List[Dict]) -> Dict[str, Dict[str, float]]:
        """Analyze sentiment for each speaker's segments using a Hugging Face model."""
        if not self.sentiment_classifier:
            logging.warning("Sentiment classifier not available.")
            return {}

        speaker_sentiments = {}
        
        for segment in diarization_data:
            speaker = segment.get('speaker', 'unknown')
            text = segment.get('text', '')
            
            if not text.strip():
                continue

            try:
                # The model returns a list of lists of dictionaries
                predictions = self.sentiment_classifier(text)
                if predictions and predictions[0]:
                    # Aggregate scores for the current segment
                    segment_scores = {p['label']: p['score'] for p in predictions[0]}
                    
                    if speaker not in speaker_sentiments:
                        speaker_sentiments[speaker] = {label: [] for label in segment_scores.keys()}
                    
                    for label, score in segment_scores.items():
                        speaker_sentiments[speaker][label].append(score)
            except Exception as e:
                logging.error(f"Error during sentiment analysis for segment '{text[:30]}...': {e}")
                continue
        
        # Calculate average sentiment scores for each speaker
        averaged_speaker_sentiments = {}
        for speaker, sentiments in speaker_sentiments.items():
            averaged_speaker_sentiments[speaker] = {
                label: np.mean(scores) if scores else 0.0 
                for label, scores in sentiments.items()
            }
            # Add a dominant emotion
            if averaged_speaker_sentiments[speaker]:
                 averaged_speaker_sentiments[speaker]['dominant_emotion'] = max(
                     averaged_speaker_sentiments[speaker].items(), key=lambda item: item[1]
                 )[0]


        return averaged_speaker_sentiments

    def calculate_all_scores(self, audio_file_path: str, full_transcript_data: Optional[Dict], diarization_data_content: Optional[Dict], hr_data: Optional[List[Dict]]) -> Dict:
        # Renamed diarization_data_content to local_diarization_data for clarity within this function
        local_diarization_data = diarization_data_content
        logging.info(f"CALC_ALL_SCORES_V3: Starting for audio file: {audio_file_path}")

        # This is the dictionary that will be returned under the 'data' key on success
        all_scores_payload = {
            "scores": {
                # Initialize main scores
                "turn_balance": {"current": 0, "original": 0, "label": "Turn Balance", "description": "Balance of speaking time."},
                "engagement_score": {"current": 0, "original": 0, "label": "Engagement Score", "description": "Overall engagement metric."},
                "clarity_score": {"current": 0, "original": 0, "label": "Clarity Score", "description": "Overall speech clarity metric."}
            },
            "detailed_metrics": {
                "turn_balance": {"current": {}, "original": {}, "label": "Turn Balance Details", "description": "Detailed turn balance data."},
                "heart_rate_metrics": {"current": {}, "original": {}, "label": "Heart Rate Analysis", "description": "Metrics from HR data."},
                "pitch_ranges": {"current": {}, "original": {}, "label": "Pitch Variation", "description": "Pitch range per speaker."},
                "speech_rates": {"current": {}, "original": {}, "label": "Speech Rate", "description": "Words per minute per speaker."},
                "silence_metrics": {"current": {}, "original": {}, "label": "Silence Analysis", "description": "Metrics on silence in conversation."},
                "sentiment_analysis": {"current": {}, "original": {}, "label": "Sentiment Analysis", "description": "Emotion detection per speaker."}
            },
            "timestamp": str(datetime.datetime.now())
        }

        try:
            logging.info("CALC_ALL_SCORES_V3: TRY_BLOCK_START")
            y_audio, sr_audio = None, None
            total_audio_duration = 0

            if os.path.exists(audio_file_path):
                try:
                    y_audio, sr_audio = librosa.load(audio_file_path, sr=None, mono=True)
                    total_audio_duration = librosa.get_duration(y=y_audio, sr=sr_audio)
                    all_scores_payload["audio_duration"] = total_audio_duration
                    logging.info(f"CALC_ALL_SCORES_V3: Audio loaded. Duration: {total_audio_duration}s")
                except Exception as e:
                    logging.error(f"CALC_ALL_SCORES_V3: Error loading audio {audio_file_path}: {e}")
                    # Not returning error yet, some scores might not need audio

            # Determine diarization source
            current_diarization_source_for_calcs = None
            diarization_source_type = "NONE"

            if local_diarization_data and "segments" in local_diarization_data and local_diarization_data["segments"]:
                current_diarization_source_for_calcs = local_diarization_data
                diarization_source_type = "DEDICATED_DIARIZATION_FILE"
            elif full_transcript_data and "diarized_segments" in full_transcript_data and full_transcript_data["diarized_segments"]:
                current_diarization_source_for_calcs = {"segments": full_transcript_data["diarized_segments"]}
                diarization_source_type = "FULL_TRANSCRIPT"
            
            logging.info(f"CALC_ALL_SCORES_V3: Using {diarization_source_type} diarization. Segments: {len(current_diarization_source_for_calcs.get('segments', [])) if current_diarization_source_for_calcs else 0}")

            # Ensure segments_for_calc is always a list
            segments_for_calc = current_diarization_source_for_calcs.get("segments", []) if current_diarization_source_for_calcs else []

            # Calculate metrics that depend on diarization_data
            if segments_for_calc:
                # Verbal Engagement (Turn Balance)
                balance_ratio_float = self.calculate_verbal_engagement(segments_for_calc)
                all_scores_payload["detailed_metrics"]["turn_balance"]["current"] = {"balance_ratio": balance_ratio_float}
                all_scores_payload["detailed_metrics"]["turn_balance"]["original"] = {"balance_ratio": balance_ratio_float}
                tb_percentage = (1 - abs(balance_ratio_float - 0.5) * 2) * 100 # 0.5 is perfect balance
                all_scores_payload["scores"]["turn_balance"]["current"] = int(round(tb_percentage))
                all_scores_payload["scores"]["turn_balance"]["original"] = int(round(tb_percentage))

                # Speech Rates
                calculated_speech_rates_wpm = self.calculate_speech_rate(segments_for_calc, total_audio_duration)
                all_scores_payload["detailed_metrics"]["speech_rates"]["current"] = calculated_speech_rates_wpm
                all_scores_payload["detailed_metrics"]["speech_rates"]["original"] = calculated_speech_rates_wpm
                
                # Silence Metrics
                silence_metrics_result = self.calculate_silence_metrics(segments_for_calc, total_audio_duration)
                all_scores_payload["detailed_metrics"]["silence_metrics"]["current"] = silence_metrics_result
                all_scores_payload["detailed_metrics"]["silence_metrics"]["original"] = silence_metrics_result

                # Pitch Ranges (requires audio loaded)
                if y_audio is not None and sr_audio is not None:
                    pitch_ranges_result = self.calculate_pitch_range_per_speaker(y_audio, sr_audio, {"segments": segments_for_calc})
                    all_scores_payload["detailed_metrics"]["pitch_ranges"]["current"] = pitch_ranges_result
                    all_scores_payload["detailed_metrics"]["pitch_ranges"]["original"] = pitch_ranges_result
                else:
                    logging.info("CALC_ALL_SCORES_V3: Skipping pitch range calculation as audio was not loaded.")

                # Sentiment Analysis
                sentiment_results = self.calculate_sentiment_analysis({"segments": segments_for_calc}) # Pass as dict
                all_scores_payload["detailed_metrics"]["sentiment_analysis"]["current"] = sentiment_results
                all_scores_payload["detailed_metrics"]["sentiment_analysis"]["original"] = sentiment_results
            else:
                logging.warning("CALC_ALL_SCORES_V3: No valid segments found in any diarization source. Skipping segment-dependent metrics.")

            # HR Metrics (if HR data is provided)
            if hr_data:
                hr_metrics_result = self.calculate_hr_metrics(hr_data, total_audio_duration)
                all_scores_payload["detailed_metrics"]["heart_rate_metrics"]["current"] = hr_metrics_result
                all_scores_payload["detailed_metrics"]["heart_rate_metrics"]["original"] = hr_metrics_result
            else:
                logging.info("CALC_ALL_SCORES_V3: Skipping HR metrics as no HR data was provided.")

            # Composite Scores
            all_scores_payload["scores"]["engagement_score"]["current"] = int(round(self._calculate_composite_engagement(all_scores_payload["detailed_metrics"])))
            all_scores_payload["scores"]["engagement_score"]["original"] = all_scores_payload["scores"]["engagement_score"]["current"]
            all_scores_payload["scores"]["clarity_score"]["current"] = int(round(self._calculate_composite_clarity(all_scores_payload["detailed_metrics"])))
            all_scores_payload["scores"]["clarity_score"]["original"] = all_scores_payload["scores"]["clarity_score"]["current"]
            
            # Convert all numpy types in the payload to standard Python types before returning
            all_scores_payload_python_types = convert_numpy_types_to_python(all_scores_payload)
            logging.info(f"CALC_ALL_SCORES_V3: TRY_BLOCK_SUCCESS. Data (first 200 chars of converted): {str(all_scores_payload_python_types)[:200]}")
            return {"success": True, "data": all_scores_payload_python_types}

        except Exception as e:
            logging.error(f"CALC_ALL_SCORES_V3: TRY_BLOCK_ERROR: {e}", exc_info=True)
            # Convert the potentially incomplete payload as well before returning error
            error_payload_python_types = convert_numpy_types_to_python(all_scores_payload)
            return {"success": False, "error": str(e), "data": error_payload_python_types}
        finally:
            logging.info(f"CALC_ALL_SCORES_V3: FINALLY_BLOCK - Exiting for {audio_file_path}.")
    
    def _save_scores(self, guid: str, scores: Dict):
        """Save scores to a JSON file"""
        scores_dir = os.path.join('static', 'uploaded_videos', 'scores')
        os.makedirs(scores_dir, exist_ok=True)
        
        scores_file = os.path.join(scores_dir, f"{guid}_scores.json")
        with open(scores_file, 'w') as f:
            json.dump(scores, f, indent=2) 

    def calculate_sentiment_analysis(self, diarization_data: Optional[Dict]) -> Dict:
        logging.debug(f"Attempting sentiment analysis. Received diarization_data (first 200 chars): {str(diarization_data)[:200]}")
        if not self.sentiment_classifier:
            logging.warning("Sentiment classifier not loaded. Skipping sentiment analysis.")
            return {}
        
        if not diarization_data or not isinstance(diarization_data, dict):
            logging.warning(f"Diarization data is not a dictionary or is None. Data type: {type(diarization_data)}. Skipping sentiment analysis.")
            return {}

        segments = diarization_data.get("segments")

        if not segments or not isinstance(segments, list) or not segments: # also check if list is empty
            logging.warning(f"No 'segments' list found in diarization_data or segments list is empty. Segments content (first 200 chars): {str(segments)[:200]}. Skipping sentiment analysis.")
            return {}

        logging.info(f"Processing {len(segments)} segments for sentiment analysis.")
        
        sentiments_by_speaker = {}
        processed_segments_count = 0
        for segment in segments: # Use the 'segments' variable
            speaker = segment.get("speaker", "Unknown Speaker")
            text = segment.get("text", "")
            if not text.strip(): # Ensure text is not just whitespace
                logging.debug(f"Skipping segment by {speaker} due to empty text.")
                continue

            try:
                max_length = self.sentiment_classifier.tokenizer.model_max_length if hasattr(self.sentiment_classifier, 'tokenizer') else 512
                
                # Tokenize to check length accurately if possible, otherwise use word count
                try:
                    inputs = self.sentiment_classifier.tokenizer(text, return_tensors=None, add_special_tokens=False) # don't return tensors yet
                    num_tokens = len(inputs['input_ids'])
                except Exception: # Fallback if tokenizer fails or not standard
                    num_tokens = len(text.split()) # Fallback to word count

                if num_tokens > max_length:
                    logging.warning(f"Segment text by {speaker} is too long ({num_tokens} tokens > {max_length}). Truncating.")
                    # Truncate based on tokens if possible, otherwise words
                    if 'input_ids' in inputs:
                         # Re-tokenize with truncation (pipeline handles this usually, but good to be aware)
                        # For simplicity, we'll let pipeline handle truncation if it does, or pass potentially still long text.
                        # A more robust truncation would happen here based on token IDs.
                        # The pipeline itself often has truncation strategies.
                        pass # Assuming pipeline handles truncation
                    else: # Fallback word-based truncation
                        text = " ".join(text.split()[:max_length-2]) # roughly account for special tokens

                prediction = self.sentiment_classifier(text) # Pipeline usually handles truncation
                
                if prediction and isinstance(prediction, list) and prediction[0] and isinstance(prediction[0], list):
                    scores_list = prediction[0] # Model returns list of lists of dicts
                    scores = {p['label']: p['score'] for p in scores_list}
                    dominant_emotion = max(scores, key=scores.get)
                    
                    if speaker not in sentiments_by_speaker:
                        sentiments_by_speaker[speaker] = {"count": 0, "scores": {label: 0.0 for label in scores.keys()}, "dominant_emotions": []}
                    
                    sentiments_by_speaker[speaker]["count"] += 1
                    for label, score_val in scores.items(): # renamed score to score_val to avoid conflict
                        sentiments_by_speaker[speaker]["scores"][label] += score_val
                    sentiments_by_speaker[speaker]["dominant_emotions"].append(dominant_emotion)
                    processed_segments_count +=1
                else:
                    logging.warning(f"Unexpected prediction format for segment by {speaker}: {str(prediction)[:100]}")


            except Exception as e:
                logging.error(f"Error during sentiment analysis for segment by {speaker} (text: '{text[:50]}...'): {e}", exc_info=True)
        
        if processed_segments_count == 0 and len(segments) > 0:
            logging.warning("No segments were successfully processed for sentiment analysis, though segments were present.")
        elif processed_segments_count > 0:
            logging.info(f"Successfully processed {processed_segments_count} out of {len(segments)} segments for sentiment.")

        final_sentiments = {}
        for speaker, data in sentiments_by_speaker.items():
            if data["count"] > 0:
                avg_scores = {label: score_sum / data["count"] for label, score_sum in data["scores"].items()}
                if data["dominant_emotions"]:
                    overall_dominant_emotion = max(set(data["dominant_emotions"]), key=data["dominant_emotions"].count)
                else:
                    overall_dominant_emotion = "N/A"
                
                final_sentiments[speaker] = {**avg_scores, "dominant_emotion": overall_dominant_emotion, "segments_analyzed": data["count"]}
        
        logging.info(f"Final sentiment analysis results: {final_sentiments}")
        return final_sentiments

    def calculate_pitch_range_per_speaker(self, y: np.ndarray, sr: int, diarization_data: Optional[Dict]) -> Dict[str, Tuple[float, float]]:
        pitch_ranges = {}
        if diarization_data is None or "segments" not in diarization_data or not diarization_data["segments"]:
            logging.warning("No diarization data for pitch range calculation.")
            return {}
        
        logging.debug(f"Calculating pitch ranges for {len(diarization_data['segments'])} segments.")
        for segment in diarization_data["segments"]:
            speaker = segment.get("speaker", "Unknown Speaker")
            start_time = segment.get("start")
            end_time = segment.get("end")

            if start_time is None or end_time is None:
                logging.warning(f"Segment for speaker {speaker} missing start/end times.")
                continue

            try:
                start_sample = librosa.time_to_samples(start_time, sr=sr)
                end_sample = librosa.time_to_samples(end_time, sr=sr)
                segment_audio = y[start_sample:end_sample]

                if len(segment_audio) == 0:
                    # logging.debug(f"Empty audio segment for {speaker} from {start_time} to {end_time}") # Can be noisy
                    continue

                pitches, magnitudes = librosa.piptrack(y=segment_audio, sr=sr)
                
                # Select pitches with high magnitude
                confident_pitches = []
                for t in range(pitches.shape[1]):
                    index = magnitudes[:, t].argmax()
                    pitch = pitches[index, t]
                    if pitch > 0:  # Filter out 0 Hz pitches
                        confident_pitches.append(pitch)
                
                if confident_pitches:
                    min_pitch = np.min(confident_pitches)
                    max_pitch = np.max(confident_pitches)
                    if speaker not in pitch_ranges:
                        pitch_ranges[speaker] = [min_pitch, max_pitch]
                    else:
                        pitch_ranges[speaker][0] = min(pitch_ranges[speaker][0], min_pitch)
                        pitch_ranges[speaker][1] = max(pitch_ranges[speaker][1], max_pitch)
            except Exception as e:
                logging.error(f"Error calculating pitch for speaker {speaker}: {e}", exc_info=True)
        logging.info(f"Pitch ranges calculated: {pitch_ranges}")
        return pitch_ranges

    # Placeholder for composite score functions
    def _calculate_composite_engagement(self, detailed_metrics: Dict) -> float:
        logging.debug(f"Calculating composite engagement with detailed_metrics: {str(detailed_metrics)[:200]}")
        tb_current = detailed_metrics.get("turn_balance", {}).get("current", {})
        # Ensure tb_current is a dict before trying to get 'balance_ratio'
        tb_score = tb_current.get("balance_ratio", 0.5) * 100 if isinstance(tb_current, dict) and tb_current else 50.0
        
        sr_data = detailed_metrics.get("speech_rates", {}).get("current", {})
        avg_sr_normalized = 0.0
        if isinstance(sr_data, dict) and sr_data:
            valid_rates = [rate for rate in sr_data.values() if isinstance(rate, (int, float))]
            if valid_rates:
                avg_sr = sum(valid_rates) / len(valid_rates)
                avg_sr_normalized = min(100.0, (avg_sr / 150.0) * 100.0) # Normalize (e.g. 150 WPM = 100%)
        
        logging.debug(f"Composite engagement: tb_score={tb_score}, avg_sr_normalized={avg_sr_normalized}")
        return (tb_score + avg_sr_normalized) / 2.0

    def _calculate_composite_clarity(self, detailed_metrics: Dict) -> float:
        logging.debug(f"Calculating composite clarity with detailed_metrics: {str(detailed_metrics)[:200]}")
        silence_metrics_current = detailed_metrics.get("silence_metrics", {}).get("current", {})
        # Ensure silence_metrics_current is a dict
        silence_ratio = silence_metrics_current.get("silence_ratio", 0.0) if isinstance(silence_metrics_current, dict) and silence_metrics_current else 0.0
        
        clarity_from_silence = (1.0 - silence_ratio) * 100.0
        pitch_contribution = 75.0 # Placeholder
        
        logging.debug(f"Composite clarity: clarity_from_silence={clarity_from_silence}, pitch_contribution={pitch_contribution}")
        return (clarity_from_silence + pitch_contribution) / 2.0 