import json
import os
import requests
from typing import Dict, Any

class DeepSeekAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate response using DeepSeek API"""
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert AI system that analyzes parent-child interactions."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False
            }

            print("Making API request with payload:", json.dumps(payload, indent=2))
            print("Using headers:", self.headers)

            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                error_message = f"Error: API returned status code {response.status_code}"
                if response.text:
                    error_message += f"\nResponse: {response.text}"
                return error_message

        except Exception as e:
            return f"Error generating response: {str(e)}"

def load_api_key() -> str:
    """Load DeepSeek API key from token file"""
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    with open(token_path, 'r') as token_file:
        return json.load(token_file)["DEEPSEEK_API_KEY"]

def analyze_interaction(transcript: str) -> Dict[str, Any]:
    """Analyze parent-child interaction using DeepSeek API"""
    prompt = f"""Analyze this parent-child interaction. The transcript contains dialogue between a parent and child, though speakers may not be explicitly labeled. If interaction quality is poor or missing, score lower rather than marking as null or N/A.

You must return ONLY a valid JSON object with exactly 6 scores between 0.0 and 1.0. Each score must have a brief explanation. Use this exact format:
{{
    "parent_responsiveness": {{
        "score": 0.0,
        "explanation": "One brief sentence explanation."
    }},
    "communication_quality": {{
        "score": 0.0,
        "explanation": "One brief sentence explanation."
    }},
    "emotional_attunement": {{
        "score": 0.0,
        "explanation": "One brief sentence explanation."
    }},
    "joint_engagement": {{
        "score": 0.0,
        "explanation": "One brief sentence explanation."
    }},
    "scaffolding": {{
        "score": 0.0,
        "explanation": "One brief sentence explanation."
    }},
    "stress_management": {{
        "score": 0.0,
        "explanation": "One brief sentence explanation."
    }}
}}

Transcript of Child and Parent Interaction:
{transcript}"""

    api = DeepSeekAPI(load_api_key())
    response = api.generate_response(prompt)
    
    try:
        # Attempt to parse the response as JSON
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse API response as JSON",
            "raw_response": response
        }

def main():
    # Load transcript
    transcript_path = "/Users/nickkleinsasser/Documents/DiarizationScoring/static/uploaded_videos/transcripts/53283d45-0e94-4c6e-a818-59bbf69baad2_transcript.json"
    with open(transcript_path, 'r') as transcript_file:
        transcript = json.load(transcript_file)["full_transcript"]

    # Analyze the interaction
    result = analyze_interaction(transcript)
    
    # Print results
    print("\nAnalysis Results:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 