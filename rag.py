import dspy
from dspy.teleprompt import BootstrapFewShot
import os
import json

PREMAI_API_KEY = os.getenv("PREMAI_API_KEY")
turbo = dspy.PremAI(model="gpt-3.5-turbo", project_id=5609, api_key=PREMAI_API_KEY, temperature=0.7, max_tokens=4000)
colbertv2_wiki17_abstracts = dspy.ColBERTv2(url='http://20.102.90.50:2017/wiki17_abstracts')
dspy.configure(lm=turbo, rm=colbertv2_wiki17_abstracts)

class GenerateQuery(dspy.Signature):
    question = dspy.InputField()
    query = dspy.OutputField(desc="a query to be used to retrieve context using a retrieval model")

class GenerateAnswer(dspy.Signature):
    context = dspy.InputField()
    question = dspy.InputField()
    textual_response = dspy.OutputField(desc="one or more paragraphs")
    data_response = dspy.OutputField(desc="a google.visualization.arrayToDataTable array of arrays in json format if applicable")
    format = dspy.OutputField(
        desc="""the most appropriate format to represent the data (formats: textual display, bar graph, table, line graph, geo chart)
            output textual display if data_response is None"""
    )

class RAG(dspy.Module):
    def __init__(self, num_passages):
        super().__init__()
        self.generate_query = dspy.ChainOfThought(GenerateQuery)
        self.retrieve = dspy.Retrieve(k=num_passages)
        self.generate_answer = dspy.ChainOfThought(GenerateAnswer)

    def forward(self, question, context=None):
        query = self.generate_query(question=question).query
        if not context:
            context = self.retrieve(query).passages
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
    relevance_question = f"The data should be helpful in answering {pred.question}. Is the data provided helpful? Yes if data is None"
    data_format_correctness_question = f"""The data should be in an array of arrays format that 
                                    can be interpreted by google.visualization.arrayToDataTable or should be None. Does the provided data do that?"""
    format_relevance_question = f"Is the format appropriate in answering {pred.question}?"
    text_relevance_question = f"Does the text provide enough text to answer the question {pred.question}?"
    format_correctness_question = f"Does it make sense to use this format on the data? (i.e format should be textual display if data is None)"
    def safe_predict(*args, **kwargs):
        try:
            return dspy.Predict(*args, **kwargs)
        except Exception as e:
            print(f"Error during prediction: {e}")
            return None
    with dspy.context(lm=gpt4T):
       data_relevance = safe_predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=relevance_question
        )
       data_format_correctness = safe_predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=data_format_correctness_question
        )
       format_relevance = safe_predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=format_relevance_question
       )
       text_relevance = safe_predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=text_relevance_question
       )
       format_correctness = safe_predict(Assess)(
            pred_question=pred.question,
            pred_text=pred.textual_response,
            pred_data=pred.data_response, 
            pred_format=pred.format, 
            assessment_question=format_correctness_question
       )
    assessments = [data_relevance, data_format_correctness, format_relevance, text_relevance, format_correctness]
    assessments = [m for m in assessments if m is not None]
    if not assessments:
        print("All predictions failed.")
        return False
    data_relevance, data_format_correctness, format_relevance, text_relevance, format_correctness = (
        [m.assessment_answer.lower() == 'yes' for m in assessments]
    )
    score = data_relevance + data_format_correctness + format_relevance + text_relevance + format_correctness
    return score >= 5

def load_trainset():
    if os.path.exists("fine_tuning_data.json"):
        with open("fine_tuning_data.json", "r") as f:
            training_set = json.load(f)
        training_set = [
            dspy.Example(
                context=obj["context"][0],
                question=obj["question"],
                textual_response=obj["textual_response"],
                data_response=obj["data_response"],
                format=obj["format"]
            )
            for obj in training_set
        ]
        training_set = [x.with_inputs("context", "question") for x in training_set]
        return training_set
    else:
        return None

def load_rag(num_passages):
    if os.path.exists("compiled_rag.json"):
        rag = RAG(num_passages=num_passages)
        rag.load("compiled_rag.json")
    else:
        trainset = load_trainset()
        if trainset is None:
            return RAG(num_passages=num_passages)
        teleprompter = BootstrapFewShot(metric=validate_prediction, max_bootstrapped_demos=2, max_labeled_demos=3)
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
    question = input(">>> ")
    if not question:
        question = "What is the GDP ranking by country"
    get_dspy_answer(question)