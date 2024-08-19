import sqlite3
import json
from main import get_local_path
import google.generativeai as genai
import pickle
import os
from main import scrape_text
from main import get_local_path


genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

def tune_generation_model():
    available_models = genai.list_models()

    con = sqlite3.connect("user_data.db")
    cur = con.cursor()

    result = cur.execute('SELECT query, response, data, format, links FROM chat')

    chats = result.fetchall()

    result_json = []
    for chat in chats:
        question = chat[0]
        response = chat[1]
        data = chat[2]
        format = chat[3]
        links = chat[4]
        context = []
        
        print(question)
        links = json.loads(links)
        for link in links:
            try:
                result = cur.execute("SELECT id, date FROM webpage WHERE url = ?", [link])
                webpage = result.fetchone()
                id = webpage[0]
                date = webpage[1]
                path = get_local_path(id, date)

                with open(path, "rb") as f:
                    content = pickle.load(f)
                
                summary = model.generate_content('Summarize the following text in detail, include all data, return None if the content or access is blocked: ' + content)
                summary = summary.text
                context.append(summary)
            except:
                continue
        entry = {
            "context": context,
            "question": question,
            "textual_response": response,
            "data_response": data,
            "format": format,
        }
        result_json.append(entry)

    con.close()
    file_path = "fine_tuning_data.json"

    with open(file_path, 'w') as json_file:
        json.dump(result_json, json_file, indent=4)

def tune_summary_model():
    con = sqlite3.connect("user_data.db")
    cur = con.cursor()

    result = cur.execute("SElECT url, id, date FROM webpage")
    entries = result.fetchall()
    
    result_json = []
    for entry in entries:
        link = entry[0]
        id = entry[1]
        date = entry[2]
        path = get_local_path(id, date)
        text = scrape_text(link)
        
        summary = model.generate_content(f"Summarize the following passage, include details and all data: {text}")
        summary = summary.text
        
        result_json.append(
            {
                "input_text": text,
                "output": summary
            }
        )

        with open("summary_data.json", 'w') as json_file:
            json.dump(result_json, json_file, indent=4)
    
    con.close()

if __name__ == "__main__":
    tune_summary_model()

