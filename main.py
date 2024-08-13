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
try:
    genai.configure(credentials=load_creds())
    name = "scrape-insight-101"
    model = genai.GenerativeModel(model_name=f'tunedModels/{name}')
except:
    model = genai.GenerativeModel("models/gemini-1.5-flash")

ph = PasswordHasher()
USER_DATA = "user_data.db"

#python
from datetime import datetime, timedelta
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging

#my lib
from cleaning import *

def init_webdriver():
    chrome_options = Options()
    #chrome_options.add_extension("Adblock Plus - free ad blocker 4.2.0.0.crx")
    chrome_options.add_argument("--headless=new")
    prefs = {
        "download.default_directory": "/dev/null",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    """    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-background-timer-throttling")"""
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

def search_brit(query):
    driver = init_webdriver()
    temp_query = query.replace(" ", "+")
    driver.get("https://www.britannica.com/search?query=" + temp_query)

    links = WebDriverWait(driver, 5).until(lambda dirver: driver.find_elements(By.CSS_SELECTOR, "#content > div > div.grid > div > ul > li > a"))
    links = [link.get_attribute("href") for link in links]

    driver.quit()
    return links

def scrape_text(link):
    driver = init_webdriver()
    driver.get(link)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    lines = [line for line in text.splitlines() if line.strip()]

    lines = list(map(clean_data, lines))

    text = " ".join(lines)
    driver.quit()

    text = model.generate_content("Summarize the following, include details and all data: " + text)
    return text.text

def get_date():
    current_datetime = datetime.now()
    format_string = "%m-%d-%y"
    current_datetime = current_datetime.strftime(format_string)

    return current_datetime

def get_last_archived_date(url):
    api_url = f'http://archive.org/wayback/available?url={url}'
    response = requests.get(api_url)
    data = response.json()
    if 'archived_snapshots' in data and 'closest' in data['archived_snapshots']:
        date_str = data['archived_snapshots']['closest']['timestamp']
        date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S').date()
        # Format the datetime object to the desired format
        return date_obj
    return None

#returns True if date collected is newer than the webpage last updated
def compare_date(date_collected, last_updated):
    if not last_updated:
        return True
    date_collected = datetime.strptime(date_collected, "%m-%d-%y").date()
    print(f"date collected: {date_collected}")
    print(f"date last updated: {last_updated}")
    
    return date_collected >= last_updated

def get_local_path(id, date):
    data_folder = "cache"
    path = str(id) + "-" + date + ".pickle"
    path = os.path.join(data_folder, path)

    return path

def collect_result(link, recursion_depth=0, max_recursion_depth=3):
    text = ""
    if link:
        print("now looking at " + link)
        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        current_datetime = get_date()
        sql_result = cur.execute("SELECT id, date FROM webpage WHERE url = ?", [link])
        webpage = sql_result.fetchone()
        last_updated = get_last_archived_date(link)
        if not webpage or not compare_date(webpage[1], last_updated): #if the entry was not found or the entry is too old, get new one
            text = scrape_text(link)
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
            else:
                cur.execute('DELETE FROM webpage WHERE url = ?', [link])
                con.commit()
                if recursion_depth < max_recursion_depth:
                    text = collect_result(link, recursion_depth + 1, max_recursion_depth)
                else:
                    print("Max recursion depth reached. Aborting.")
    con.close()
    return text

def iter_result(links):
    result = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(lambda l: collect_result(l), link): link for link in links}
        for future in as_completed(futures):
            try:
                result.append(future.result())
            except Exception as exc:
                print(f"An error occurred: {exc}")
    print(f"{len(result)} elements in result")
    return result

def get_AI_response(query, input_list, chat=None, recursion_depth=0, max_recursion_depth=3):
    result = None
    try:
        context = " ".join(input_list)
        result = model.generate_content(f"context: {context} question: {query}")
        result = result.text
        result = markdown.markdown(result, extensions=['nl2br'])
        print(result)
        result = json.loads(result[result.find("{"):result.rfind("}") + 1])
        textual_response, data_response = result.get("textual response"), result.get("data response")
        if data_response:
            data_response.replace("'", '"')
            json.loads(data_response)
        top_format = result.get("format") if textual_response and data_response else "textual display"
        return textual_response, data_response, top_format
    except Exception as e:
        if isinstance(e, json.JSONDecodeError):
            return result, None, "textual display"
        logging.error("An error occured", exc_info=True)
        if recursion_depth < max_recursion_depth:
            return get_AI_response(query, input_list, chat, recursion_depth + 1, max_recursion_depth)