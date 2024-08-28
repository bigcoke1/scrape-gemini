import sqlite3
import json
import logging
import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

def tune_generation_model():
    con = sqlite3.connect("user_data.db")
    cur = con.cursor()

    result = cur.execute('SELECT query, response, data, format, links FROM chat')

    chats = result.fetchall()

    result_json = []
    for chat in chats:
        try:
            question = chat[0]
            response = chat[1]
            data = chat[2]
            format = chat[3]
            context = "Some context..."
            
            if data is None:
                data =[]
            
            entry = {
                "context": context,
                "question": question,
                "textual_response": response,
                "data_response": data,
                "format": format,
            }
            result_json.append(entry)
            file_path = "training_set.json"
            with open(file_path, 'w') as json_file:
                json.dump(result_json, json_file, indent=4)
        except:
            logging.error("An error occured", exc_info=True)
            continue

    con.close()

if __name__ == "__main__":
    tune_generation_model()

