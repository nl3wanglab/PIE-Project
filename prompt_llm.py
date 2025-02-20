import json
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login

def setup_device():
    """Determine and configure the best available device"""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def load_model(model_name, device, auth_token):
    """Load model with appropriate settings based on device"""
    print(f"🔹 Loading model: {model_name} on {device}")
    
    # Base configuration for all devices
    model_kwargs = {
        "trust_remote_code": True,
        "token": auth_token,
        "device_map": "auto",
        "low_cpu_mem_usage": True
    }
    
    # Device-specific optimizations
    if device == "cuda":
        model_kwargs["torch_dtype"] = torch.float16
    elif device == "cpu":
        model_kwargs["torch_dtype"] = torch.float32
    elif device == "mps":
        model_kwargs["torch_dtype"] = torch.float16
        os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
        torch.mps.empty_cache()
    
    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, token=auth_token)
    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    
    return model, tokenizer

def generate_response(model, tokenizer, prompt, device, max_new_tokens=500):
    """Generate response with optimized settings per device"""
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    inputs = inputs.to(device)
    
    generation_config = {
        "max_new_tokens": max_new_tokens,
        "do_sample": True,
        "temperature": 0.7,
        "top_k": 50,
        "top_p": 0.9,
        "pad_token_id": tokenizer.eos_token_id,
        "repetition_penalty": 1.2,
        "no_repeat_ngram_size": 3,
        "num_return_sequences": 1,
        "max_length": 1000,
        "min_length": 50,
        "early_stopping": True
    }
    
    try:
        with torch.no_grad():
            if device == "mps":
                model.to('cpu')
                inputs = inputs.to('cpu')
                outputs = model.generate(inputs.input_ids, **generation_config)
                model.to(device)
            else:
                outputs = model.generate(inputs.input_ids, **generation_config)
        
        # Only decode the new tokens (excluding the prompt)
        prompt_length = inputs.input_ids.shape[1]
        generated_tokens = outputs[0][prompt_length:]
        return tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
    except Exception as e:
        return f"Error generating response: {str(e)}"

def analyze_prompt_tokens(tokenizer, prompt, transcript):
    """Analyze token usage of the prompt and transcript separately"""
    # Analyze base prompt without transcript
    base_prompt = prompt.replace(transcript, "")
    base_tokens = tokenizer(base_prompt, return_tensors="pt")
    base_token_count = len(base_tokens.input_ids[0])
    
    # Analyze transcript alone
    transcript_tokens = tokenizer(transcript, return_tensors="pt")
    transcript_token_count = len(transcript_tokens.input_ids[0])
    
    # Analyze full prompt
    full_tokens = tokenizer(prompt, return_tensors="pt")
    total_tokens = len(full_tokens.input_ids[0])
    
    print(f"\nPrompt Analysis:")
    print(f"Base prompt tokens: {base_token_count}")
    print(f"Transcript tokens: {transcript_token_count}")
    print(f"Total tokens: {total_tokens}")
    print(f"Token limit: {tokenizer.model_max_length}")
    print(f"Tokens remaining: {tokenizer.model_max_length - total_tokens}")
    return total_tokens

def main():
    # Load authentication token
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    with open(token_path, 'r') as token_file:
        auth_token = json.load(token_file)["HUGGING_FACE_TOKEN"]
    
    # Login to Hugging Face
    login(auth_token)
    
    # Setup device and model
    device = setup_device()
    
    phi_2 = "microsoft/phi-2"
    phi_3_mini = "microsoft/phi-3-mini-128k-instruct"

    model_name = phi_3_mini
    model, tokenizer = load_model(model_name, device, auth_token)
    
    # Load transcript
    transcript_path = "/Users/nickkleinsasser/Documents/DiarizationScoring/static/uploaded_videos/transcripts/77562204-d386-4fc9-a942-b3eb6886880f_transcript.json"
    with open(transcript_path, 'r') as transcript_file:
        transcript = json.load(transcript_file)["full_transcript"]

    
    
    # Create prompt
    prompt = f"""<|system|>
You are an expert AI system that analyzes parent-child interactions. You must return ONLY a valid JSON object with exactly 6 scores between 0.0 and 1.0. Each score must have a brief explanation. Use this exact format:
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
}}<|end|>
<|user|>
Analyze this parent-child interaction. The transcript contains dialogue between a parent and child, though speakers may not be explicitly labeled. If interaction quality is poor or missing, score lower rather than marking as null or N/A.

Transcript of Child and Parent Interaction:
{transcript}
<|end|>
<|assistant|>
"""
    
    # Analyze token usage
    analyze_prompt_tokens(tokenizer, prompt, transcript)
    
    # Generate and print raw response
    response = generate_response(model, tokenizer, prompt, device)
    print("\nModel Response:")
    print(response)

if __name__ == "__main__":
    main()