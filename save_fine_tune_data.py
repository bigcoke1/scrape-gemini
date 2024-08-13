import sqlite3
import json
from main import get_local_path
import google.generativeai as genai
import pickle
import os
import time

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
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