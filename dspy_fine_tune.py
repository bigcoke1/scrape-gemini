import dspy

class Summarize(dspy.Signature):
    context = dspy.InputField()
    summary = dspy.OutputField()

class GenerateResponse(dspy.Signature):
    summary = dspy.InputField()
    question = dspy.InputField()
    textual_response = dspy.OutputField(desc="response to question in plain text")
    data_response = dspy.OutputField(desc="an array of array in descending order if it involves ranking or ascending order if it involves time, numerical data preffered")
    display_format = dspy.OutputField(desc="""what type of visual display the user is asking 
        (i.e. bar graph, pie chart, scatterplot, line graph, histogram, table, textual display, area chart, bubble chart, 
        histogram, geo chart, donut chart, and gauge chart""")

def validate_context_and_answer(example, pred, trace=None):
   answer_EM = dspy.evaluate.answer_exact_match(example, pred)
   answer_PM = dspy.evaluate.answer_passage_match(example, pred)
   return answer_EM and answer_PM

if __name__ == "__main__":
    print("Loading dataset...")
    
    print("Dataset loaded")