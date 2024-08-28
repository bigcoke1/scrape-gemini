import weaviate
from weaviate.classes.init import Auth
import weaviate.classes as wvc
import os
import json

# Set these environment variables
URL = os.getenv("WCS_TEST_URL")
APIKEY = os.getenv("WCS_ADMIN_KEY")

def instantiate_weaviate() -> weaviate.Client:
    # Connect to a WCS instance
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=URL,  # Replace with your Weaviate Cloud URL
        auth_credentials=Auth.api_key(APIKEY),  # Replace with your Weaviate Cloud key
        headers={
            "X-Azure-Api-Key": os.getenv("AZURE_APIKEY")
        }
    )
    return client

if __name__ == "__main__":
    try: 
        client = instantiate_weaviate()
        print(client.is_ready())
        client.collections.delete("Privacy_Data")
        questions = client.collections.create(
            name="Privacy_Data",
            vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_azure_openai(resource_name="easonmopenai", deployment_id="weaviate"),  # If set to "none" you must always provide vectors yourself. Could be any other "text2vec-*" also.
            generative_config=wvc.config.Configure.Generative.azure_openai(resource_name="easonmopenai", deployment_id="weaviate")  # Ensure the `generative-openai` module is used for generative queries
        )
        
        json_path = ""
        if json_path:
            with open(json_path, "r") as f:
                data = json.loads(f)  # Load data
        else:
            data = [{"Answer": "example", "Question": "this is an example"}]

        question_objs = list()
        for i, d in enumerate(data):
            question_objs.append({
                "answer": d["Answer"],
                "question": d["Question"]
            })

        questions = client.collections.get("Privacy_Data")
        questions.data.insert_many(question_objs)

        questions = client.collections.get("Privacy_Data")

        response = questions.query.near_text(
            query="example",
            limit=2
        )

        print(response.objects[0].properties) 
    finally:
        client.close()