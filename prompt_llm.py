import json
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login

# Load Hugging Face token from file
token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
with open(token_path, 'r') as token_file:
    auth_token = json.load(token_file)["HUGGING_FACE_TOKEN"]

# Log in to Hugging Face (optional but recommended)
login(auth_token)

# 🔹 AVAILABLE MODELS (Choose one)
MODEL_OPTIONS = {
    "mistral": "mistralai/Mistral-7B-Instruct-v0.1",
    "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", # 2.2 gb
    "mobilama": "microsoft/MobiLlama-0.5B",
    "teenytinyllama": "TeenyTinyLlama/TeenyTinyLlama-100M",
    "phi2": "microsoft/phi-2" # 5 gb
}

# Change this to switch between models
selected_model = "phi2"  # Options: "mistral", "tinyllama", "mobilama", "teenytinyllama", "phi2"

# Get model name
model_name = MODEL_OPTIONS[selected_model]

print(f"🔹 Loading model: {model_name}")

# Move model to available device
device = "cpu" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")

# Load tokenizer & model
tokenizer = AutoTokenizer.from_pretrained(model_name, device_map=device, trust_remote_code=True, token=auth_token)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map=device, trust_remote_code=True, token=auth_token)

model.to(device)

# Function to generate responses & enforce JSON output
def generate_response(prompt, max_length=25600, max_retries=3):
    for attempt in range(max_retries):
        inputs = tokenizer(prompt, return_tensors="pt").to(device)

        with torch.no_grad():
            generated_ids = model.generate(inputs.input_ids, max_new_tokens=max_length, do_sample=True)

        output_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        print(f"📝 Attempt {attempt+1} Output:\n{output_text}\n")

        # Extract JSON if model adds extra text
        json_start = output_text.find("{")
        json_end = output_text.rfind("}")
        if json_start != -1 and json_end != -1:
            output_text = output_text[json_start:json_end+1]  # Extract only JSON

        # Attempt to parse JSON
        try:
            response_json = json.loads(output_text)
            return response_json  # Return valid parsed JSON
        except json.JSONDecodeError:
            print(f"⚠️ Attempt {attempt+1} failed: Model did not return valid JSON. Retrying...")

    return {"error": "Model failed to return valid JSON after multiple attempts."}

# 🔹 Example Transcript
transcript = """
Mike: Hello, how are you?
Bob: I'm good, how are you?
Mike: I'm good too.
Bob: That's great to hear.
Mike: The weather is sunny.
Bob: Yes, it's a beautiful day.
"""

# 🔹 Strong JSON-Enforced Prompt
scoring_prompt = r"""
Assistant is an intelligent Co-Pilot designed to evaluate a transcript interaction between a child and parent.
Assistant's instructions contain markers inside of < > symbols. These are markers for the assistant to find information and should not be returned in Assistant's response.
Evaluation Process
Start with a base score of <Base Score: 1.0> and adjust based on key interaction aspects found in <Transcript>.
Key Factors for Evaluation
<Emotional Tone>
<Supportive & empathetic> → <No Penalty>
<Neutral or indifferent> → <Small Penalty>
<Dismissive or invalidating> → <Larger Penalty>
<Engagement & Active Listening>
<Engaged, acknowledges childs feelings> → <No Penalty>
<Somewhat engaged but lacking depth> → <Small Penalty>
<Distracted, dismissive, or ignoring key points> → <Larger Penalty>
<Guidance & Encouragement>
<Provides constructive advice or encouragement> → <No Penalty>
<Gives neutral or unclear guidance> → <Small Penalty>
<No guidance, discouraging, or critical> → <Larger Penalty>
<Respect & Communication Style>
<Respects childs perspective, uses calm tone> → <No Penalty>
<Occasionally interrupts or talks over child> → <Small Penalty>
<Dominates conversation, invalidates childs viewpoint> → <Larger Penalty>
<Conflict Handling (if applicable)>
<Resolves disagreements calmly> → <No Penalty>
<Some tension but no escalation> → <Small Penalty>
<Escalates conflict, unresolved frustration> → <Larger Penalty>
<Final Score Calculation>
Start at <1.0> and subtract <Penalties> dynamically based on <Severity> of issues in <Transcript>.
<Output Format>
{
  "Final Interaction Score": <double>
}
<Transcript>
"""

scoring_prompt += transcript
scoring_prompt += "\n</Transcript>"

# Generate Scored Response
scored_response = generate_response(scoring_prompt)

# Output final JSON result
#output_json = json.dumps(scored_response, indent=4)
print(scored_response)