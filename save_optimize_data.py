import sqlite3
import json
from google_init import *
import google.generativeai as genai
import pickle
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

def tune_generation_model():
    con = sqlite3.connect("user_data.db")
    cur = con.cursor()

    result = cur.execute('SELECT query, response, data, format, links FROM chat')

    chats = result.fetchall()

    with open("fine_tuning_data.json", "r") as f:
        result_json = json.load(f)
    for chat in chats:
        try:
            question = chat[0]
            response = chat[1]
            data = chat[2]
            format = chat[3]
            links = chat[4]
            context = []
            for link in links:
                result = cur.execute('SELECT id, date FROM webpage WHERE url = ?', [link])
                webpage = result.fetchone()
                id = webpage[0]
                date = webpage[1]

                path = get_local_path(id, date)
                with open(path, "rb") as f:
                    summary = pickle.load(f)
                context.append(summary)
            
            entry = {
                "context": context,
                "question": question,
                "textual_response": response,
                "data_response": data,
                "format": format,
            }
            result_json.append(entry)
            file_path = "fine_tuning_data.json"
            with open(file_path, 'w') as json_file:
                json.dump(result_json, json_file, indent=4)
        except:
            logging.error("An error occured", exc_info=True)
            continue

    con.close()

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
    tune_generation_model()

