#third-party
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pickle
import google.generativeai as genai
import markdown
import requests

from argon2 import PasswordHasher

#my lib
from load_creds import load_creds
genai.configure(credentials=load_creds())
time_model = genai.GenerativeModel(model_name=f'tunedModels/scrape-insight-time-model')
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash", generation_config={"temperature": 0.2})

ph = PasswordHasher()
USER_DATA = "user_data.db"

#python
from datetime import datetime, timedelta
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import time

#my lib
from cleaning import *

def init_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    prefs = {
        "download.default_directory": "/dev/null",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.binary_location = "/home/easonmeng/chrome-linux64/chrome"
    
    driver = webdriver.Chrome(options=chrome_options)

    return driver

#web crawls google search
def search_google(query):
    driver = init_webdriver()
    temp_query = clean_query(query).replace(" ", "+")
    driver.get("https://www.google.com/search?q=" + temp_query)

    titles = WebDriverWait(driver, 5).until(lambda driver: driver.find_elements(By.CSS_SELECTOR, "#search h3"))
    titles = [title for title in titles if "".join(title.text.split())]
    links = [title.find_element(By.XPATH, "./..") for title in titles]
    links = [link.get_attribute("href") for link in links]

    driver.quit()
    return links

def scrape_text(link):
    try:
        response = requests.get(link, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            text = soup.get_text()
            lines = [line for line in text.splitlines() if line.strip()]
            lines = list(map(clean_data, lines))
            text = " ".join(lines)
            return text
        else:
            raise Exception
    except:
        print(f"An error occurred: {response.status_code} error")

def get_date():
    current_datetime = datetime.now()
    format_string = "%m-%d-%y"
    current_datetime = current_datetime.strftime(format_string)

    return current_datetime

def get_day_tolerence(query):
    prompt = f"Instruction: Determine how fresh the data needs to be for the following question. Question: {query}"
    day_tolerence = time_model.generate_content(prompt)
    day_tolerence = day_tolerence.text
    day_tolerence = ''.join(re.findall(r'\d+', day_tolerence))
    print(f"day tolerence: {day_tolerence.strip()} days")
    return float(day_tolerence)

def compare_date(date, day_tolerence):
    date = datetime.strptime(date, "%m-%d-%y").date()
    return abs(date - datetime.now().date()) < timedelta(days=day_tolerence)

def get_local_path(id, date):
    data_folder = "cache"
    path = str(id) + "-" + date + ".pickle"
    path = os.path.join(data_folder, path)

    return path

def collect_result(link, day_tolerence, current_chat, recursion_depth=0, max_recursion_depth=3):
    text = ""
    if link:
        print("now looking at " + link)
        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        current_datetime = get_date()
        sql_result = cur.execute("SELECT id, date FROM webpage WHERE url = ?", [link])
        webpage = sql_result.fetchone()
        if not webpage or not compare_date(webpage[1], day_tolerence): #if the entry was not found or the entry is too old, get new one
            text = scrape_text(link)
            text = current_chat.send_message("Summarize the following, include details and all data: " + text)
            text = text.text
            if webpage: #if the entry was found but is too old
                cur.execute("DELETE FROM webpage WHERE url = ?", [link])
                path = get_local_path(webpage[0], webpage[1])
                try:
                    os.remove(path)
                    print(f"old file detected and deleted: {path}")
                except Exception as e:
                    print(f"An Error Occurred: {e}")

            cur.execute("INSERT INTO webpage (url, date) VALUES (?, ?)", [link, current_datetime])
            
            sql_result = cur.execute("SELECT id, date FROM webpage WHERE url = ?", [link])
            webpage = sql_result.fetchone()

            path = get_local_path(webpage[0], current_datetime)
            with open(path, "wb") as f:
                pickle.dump(text, f)
            print("new file created: " + path)
            con.commit()
        else:
            path = get_local_path(webpage[0], webpage[1])
            if os.path.exists(path):
                print("reading existing file: " + path)
                with open(path, "rb") as f:
                    text = pickle.load(f)
                current_chat.send_message(text)
            else:
                cur.execute('DELETE FROM webpage WHERE url = ?', [link])
                con.commit()
                if recursion_depth < max_recursion_depth:
                    print(f"Error occured. Recursion depth: {recursion_depth}")
                    text = collect_result(link, day_tolerence, recursion_depth + 1, max_recursion_depth)
                else:
                    print("Max recursion depth reached. Aborting.")
    con.close()
    return text

def iter_result(query, links, current_chat):
    day_tolerence = get_day_tolerence(query)
    result = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(lambda l: collect_result(l, day_tolerence, current_chat), link): link for link in links}
        for future in as_completed(futures):
            try:
                result.append(future.result())
                if len(result) >= 5:
                    print(f"{len(result)} elements in result")
                    return current_chat
            except Exception as exc:
                print(f"An error occurred: {exc}")
    return current_chat

def get_AI_response(query, chat, recursion_depth=0, max_recursion_depth=3):
    textual_response = None
    try:
        print(clean_query(query))
        textual_response = chat.send_message("Using all previous context and your own knowledge, tell me about this in plain text:" + query)
        textual_response = textual_response.text
        textual_response = markdown.markdown(textual_response, extensions=['nl2br'])
        print(textual_response)
        
        data_response = chat.send_message("""Based on all previous context, make a google.visualization.arrayToDataTable array of array in json format to represent the data, numerical data preferred,
                                          descending order unless the independent variable is time
                                          (Example: 
                                          [["blah", "blah"], ["blah", 10], ["blah", 10], ["blah", 10], ["blah", 10]]
                                          )
                                          if a data response if not applicable, return "null"
                                          DO NOT RETURN ANYTHING ELSE EXCEPT THE ARRAY, NO EXPLANATION
                                          """)
        data_response = data_response.text
        data_response = data_response[data_response.find("["):data_response.rfind("]") + 1]
        print(data_response)

        format = chat.send_message(f"""Based on the previous context, in these formats, which one is the most appropriate to represent the data you just provided?
                                   query: {query}
                                   formats: textual display, bar graph, table, line graph, geo chart
                                   if no data is provided earlier, return "textual display"
                                   DO NOT RETURN ANYTHING ELSE EXCEPT THE NAME OF THE DISPLAY (NO EXPLANATION)
                                   """)
        format = format.text
        format = format.strip()
        print(format)
        return textual_response, data_response, format
    except Exception as e:
        logging.error("An error occured", exc_info=True)
        if recursion_depth < max_recursion_depth:
            return get_AI_response(query, chat, recursion_depth + 1, max_recursion_depth)
        else:
            return textual_response, None, "textual display"