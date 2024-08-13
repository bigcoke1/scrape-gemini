import pprint
import google.generativeai as genai
from load_creds import load_creds
import json

creds = load_creds()

genai.configure(credentials=creds)

base_model = [
    m for m in genai.list_models()
    if "createTunedModel" in m.supported_generation_methods][1]

with open("fine_tuning_data.json", "r") as f:
    training_data = json.load(f)

formatted_data = []

for item in training_data:
    # Combine context and question to create a meaningful text input
    text_input = f"{item['context']} Question: {item['question']}"
    
    # Assuming 'textual response' is the output you want to predict
    output = {
        "textual response": item["textual_response"],
        "data response": item["data_response"],
        "format": item["format"]
    }

    # Convert the dictionary to a JSON string
    output = json.dumps(output)

    # Create a new dictionary with the expected keys
    formatted_data.append({
        "text_input": text_input,
        "output": output
    })

name = f"scrape-insight-101"
operation = genai.create_tuned_model(
    source_model=base_model,
    training_data=formatted_data,

    id = name,
    epoch_count = 5,
    batch_size=4,
    learning_rate=0.001,
)

tuned_models = genai.list_tuned_models()
tuned_models = [m for m in tuned_models]
print(tuned_models)