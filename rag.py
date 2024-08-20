import dspy
from dspy.teleprompt import BootstrapFewShot
import os
import json

OPENAI_API_KEY = os.getenv("OPENAI_AI_KEY")
turbo = dspy.OpenAI("gpt-3.5-turbo", OPENAI_API_KEY)
colbertv2_wiki17_abstracts = dspy.ColBERTv2(url='http://20.102.90.50:2017/wiki17_abstracts')
dspy.configure(lm=turbo, rm=colbertv2_wiki17_abstracts)


class GenerateQuery(dspy.Signature):
    question = dspy.InputField()
    query = dspy.OutputField()

class GenerateAnswer(dspy.Signature):
    context = dspy.InputField()
    question = dspy.InputField()
    textual_response = dspy.OutputField()
    data_response = dspy.OutputField(desc="a google.visualization.arrayToDataTable array of arrays in json format")
    format = dspy.OutputField()

class RAG(dspy.Module):
    def __init__(self, num_passages):
        super().__init__()
        self.generate_query = dspy.ChainOfThought(GenerateQuery)
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate_answer = dspy.ChainOfThought(GenerateAnswer)

    def forward(self, question):
        query = self.generate_query(question=question).query
        context = self.retrieve(query).passages
        pred = self.generate_answer(context=context, question=question)
        return dspy.Prediction(context=context, question=question, textual_response=pred.textual_response, data_response=pred.data_response, format=pred.format)

gpt4T = dspy.OpenAI(model="gpt-4-1106-preview", max_tokens=1000, model_type="chat")
class Assess(dspy.Signature):
    pred_question = dspy.InputField()
    pred_text = dspy.InputField()
    pred_data = dspy.InputField()
    pred_format = dspy.InputField()
    assessment_question = dspy.InputField()
    asessment_answer = dspy.OutputField(desc="Yes or No")

def validate_prediction(example, pred, trace=None):
    relevance_question = f"The data should be helpful in answering {pred.question}. Is the data provided helpful?"
    format_correctness_question = f"The data should be in an array of arrays format that can be interpreted by google.visualization.arrayToDataTable. Does the provided data do that?"
    with dspy.context(lm=gpt4T):
       data_relevance = dspy.Predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=relevance_question
        )
       data_format_correctness = dspy.Predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=format_correctness_question
        )
    data_relevance, data_format_correctness = [m.assessment_asnwer.lower() == 'yes' for m in [data_relevance, data_format_correctness]]
    score = data_relevance + data_format_correctness
   
    if trace is not None: return score >= 2
    return score / 2.0

def load_trainset():
    if os.path.exists("training_set.json"):
        with open("training_set.json", "r") as f:
            training_set = json.loads(f)
        training_set = [
            dspy.Example(
                question=obj["question"],
                textual_response=obj["textual_response"],
                data_response=obj["data_response"],
                format=obj["format"]
            )
            for obj in training_set
        ]
        training_set = [x.with_inputs("question") for x in training_set]
        return training_set
    else:
        return None

def load_rag(num_passages):
    if os.path.exists("compiled_rag.json"):
        rag = RAG(num_passages=num_passages)
        rag.load("compiled_rag.json")
    else:
        teleprompter = BootstrapFewShot(metric=validate_prediction)
        trainset = load_trainset()
        if trainset is None:
            return RAG(num_passages=num_passages)
        rag = teleprompter.compile(RAG(num_passages=num_passages), trainset=trainset)
        rag.save("compiled_rag.json")
    return rag

def get_dspy_answer(question):
    rag = load_rag(num_passages=5)
    pred = rag(question)
    print(f"Question: {question}")
    print(f"Predicted Textual Response: {pred.textual_response}")
    print(f"Predicted Data Response: {pred.data_response}")
    print(f"Predicted Format: {pred.format}")
    print(f"Retrieved Contexts (truncated): {[c[:200] + '...' for c in pred.context]}")
    return pred.textual_response, pred.data_response, pred.format

if __name__ == "__main__":
    get_dspy_answer("What is the current GDP ranking by country")