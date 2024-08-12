import pprint
import google.generativeai as genai
from load_creds import load_creds

creds = load_creds()

genai.configure(credentials=creds)

base_model = [
    m for m in genai.list_models()
    if "createTunedModel" in m.supported_generation_methods][1]
print(base_model)

name = f"scrape-insight-100"
operation = genai.create_tuned_model(
    source_model=base_model,
    training_data=[],

    id = name,
    epoch_count = 100,
    batch_size=4,
    learning_rate=0.001,
)