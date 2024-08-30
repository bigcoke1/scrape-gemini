import dspy
from dspy.teleprompt import BootstrapFewShotWithRandomSearch
from dspy.retrieve.weaviate_rm import WeaviateRM
from weaviate_init import instantiate_weaviate
import os
import json
import logging

TRAINING_SET_PATH = "training_set.json"
PREMAI_API_KEY = os.getenv("PREMAI_API_KEY")
turbo = dspy.PremAI(model="gpt-3.5-turbo", project_id=5609, api_key=PREMAI_API_KEY, temperature=0.2, max_tokens=4000)
colbertv2_wiki17_abstracts = dspy.ColBERTv2(url='http://20.102.90.50:2017/wiki17_abstracts')
with instantiate_weaviate() as weaviate_client:
    weaviate_rm = WeaviateRM(weaviate_collection_name="Privacy_Data", weaviate_client=weaviate_client)
dspy.settings.configure(lm=turbo, rm=colbertv2_wiki17_abstracts, backoff_time=5)

class GenerateAnswer(dspy.Signature):
    context = dspy.InputField(desc="May contain useful information")
    question = dspy.InputField()
    textual_response = dspy.OutputField(desc="at least two paragraphs using your own knowledge and the context, include details, in html format")
    data_response = dspy.OutputField(desc="a google.visualization.arrayToDataTable array of arrays in json format if applicable")
    format = dspy.OutputField(
        desc="""the most appropriate format to represent the data (formats: textual display, bar graph, table, line graph, geo chart)
            output textual display if data response is []"""
    )

class RAG(dspy.Module):
    def __init__(self, num_passages, custom_rm=None):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate_answer = dspy.ChainOfThought(GenerateAnswer)
        self.custom_rm = custom_rm

    def forward(self, question, context=None):
        if not context:
            context = []
            if self.custom_rm is not None:
                try:
                    dspy.settings.configure(rm=self.custom_rm)
                    context = self.retrieve(question).passages
                except:
                    pass
            dspy.settings.configure(rm=colbertv2_wiki17_abstracts)
            context = context + self.retrieve(question).passages
        pred = self.generate_answer(context=context, question=question)
        return dspy.Prediction(context=context, question=question, textual_response=pred.textual_response, data_response=pred.data_response, format=pred.format)

gpt4T = dspy.PremAI(model="gpt-4-turbo", project_id=5609, api_key=PREMAI_API_KEY, temperature=0.5, max_tokens=10)
class Assess(dspy.Signature):
    pred_question = dspy.InputField()
    pred_text = dspy.InputField()
    pred_data = dspy.InputField()
    pred_format = dspy.InputField()
    assessment_question = dspy.InputField()
    assessment_answer = dspy.OutputField(desc="Yes or No")

def validate_prediction(example, pred, trace=None):
    data_format_correct = True
    try:
        json.loads(pred.data_response)
    except:
        data_format_correct = False

    if trace is None:
        return data_format_correct
    else:
        return int(data_format_correct)

def load_trainset():
    if os.path.exists(TRAINING_SET_PATH):
        with open(TRAINING_SET_PATH, "r") as f:
            training_set = json.load(f)
        training_set = [
            dspy.Example(
                context=obj["context"],
                question=obj["question"],
                textual_response=obj["textual_response"][:200],
                data_response=str(obj["data_response"]),
                format=obj["format"]
            )
            for obj in training_set
        ]
        training_set = [x.with_inputs("context", "question") for x in training_set]
        return training_set
    else:
        return None

def load_rag(num_passages, custom_rm):
    try:
        if os.path.exists("compiled_rag_random.json"):
            rag = RAG(num_passages=num_passages, custom_rm=custom_rm)
            rag.load("compiled_rag_random.json")
        else:
            trainset = load_trainset()
            if trainset is None:
                return RAG(num_passages=num_passages, custom_rm=custom_rm)
            teleprompter = BootstrapFewShotWithRandomSearch(metric=validate_prediction, max_bootstrapped_demos=2, max_labeled_demos=3, num_candidate_programs=3, num_threads=4)
            rag = teleprompter.compile(student=RAG(num_passages=num_passages, custom_rm=custom_rm), trainset=trainset)
            rag.save("compiled_rag_random.json")
        return rag
    except:
        logging.error("An error occured", exc_info=True)

def get_dspy_answer(question, username):
    rag = load_rag(num_passages=5, custom_rm=init_rm(username))
    pred = rag(question)
    print(f"Question: {question}")
    print(f"Predicted Textual Response: {pred.textual_response}")
    print(f"Predicted Data Response: {pred.data_response}")
    print(f"Predicted Format: {pred.format}")
    print(f"Retrieved Contexts (truncated): {[c[:200] + '...' for c in pred.context]}")
    return pred.textual_response, pred.data_response, pred.format

def init_rm(username):
    try:
        weaviate_client = instantiate_weaviate()
        weaviate_rm = WeaviateRM(weaviate_collection_name=username, weaviate_client=weaviate_client, weaviate_collection_text_key="passage")
        return weaviate_rm
    except:
        return None

if __name__ == "__main__":
    question = input(">>> ")
    if not question:
        question = "What is the GDP ranking by country"
    get_dspy_answer(question)