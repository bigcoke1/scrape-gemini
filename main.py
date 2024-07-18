#third-party
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pickle
import google.generativeai as genai

from argon2 import PasswordHasher

model = genai.GenerativeModel("gemini-1.5-flash")
ph = PasswordHasher()
USER_DATA = "user_data.db"

#python
from datetime import datetime, timedelta
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

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
    return text

def compare_date(date):
    date = datetime.strptime(date, "%m-%d-%y").date()
    return abs(date - datetime.now().date()) <= timedelta(days=3)

def get_date():
    current_datetime = datetime.now()
    format_string = "%m-%d-%y"
    current_datetime = current_datetime.strftime(format_string)

    return current_datetime

def get_local_path(id, date):
    data_folder = "data"
    path = str(id) + "-" + date + ".pickle"
    path = os.path.join(data_folder, path)

    return path

def collect_result(link):
    text = ""
    if link:
        print("now looking at " + link)
        con = sqlite3.connect(USER_DATA)
        cur = con.cursor()
        current_datetime = get_date()
        sql_result = cur.execute("SELECT id, date FROM webpage WHERE url = ?", [link])
        webpage = sql_result.fetchone()
        if not webpage or not compare_date(webpage[1]): #if the entry was not found or the entry is too old, get new one
            text = scrape_text(link)
            if webpage: #if the entry was found but is too old
                print("old file detected and deleted")
                cur.execute("DELETE FROM webpage WHERE url = ?", [link])
                path = get_local_path(webpage[0], webpage[1])
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"An Error Occured: {e}")

            cur.execute("INSERT INTO webpage (url, date) VALUES (?, ?)", [link, current_datetime])
            
            sql_result = cur.execute("SELECT id, date FROM webpage WHERE url = ?", [link])
            webpage = sql_result.fetchone()

            path = get_local_path(webpage[0], current_datetime)
            with open(path, "wb") as f:
                pickle.dump(text, f)
            print("new file created: " + path)
            con.commit()
            con.close()
        else:
            path = get_local_path(webpage[0], webpage[1])
            print("reading existing file: " + path)
            with open(path, "rb") as f:
                text = pickle.load(f)
    return text

def iter_result(links):
    result = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(collect_result, link): link for link in links}
        for future in as_completed(futures):
            try:
                result.append(future.result())
            except Exception as exc:
                print(f"An error occurred: {exc}")
    print(f"{len(result)} elements in result")
    print("no duplicates?: " + str(len(result) == len(set(result))))
    return result

def split_long_string(data, max_length):
    result = []
    for entry in data:
        if len(entry) > max_length:
            chunks = [entry[i:i+max_length] for i in range(0, len(entry), max_length)]
            result.extend(chunks)
        else:
            result.append(entry)
    return result

def get_AI_response(query, input_list):
    print(query)
    prompt_format = """
        Give me a JSON (and only the JSON enclosed with '{}' with no explanation) of what type of visual display the user is asking 
        (i.e. bar graph, pie chart, scatterplot, line graph, histogram, table, textual display, and 2 more displays you think it's possible)
        where each key is the type of visual display and each value is the probability that the user is asking for that display.
        The prompt is: 
    """ + query
    format = model.generate_content(prompt_format)
    format = format.text
    format_dict = json.loads(format)
    if format_dict:
        top_format = max(format_dict, key=format_dict.get)     
    else:
        top_format = "textual display"
    
    print(top_format)

    input_list = split_long_string(input_list, 10000)
    
    prompt = f"""Using information provided above, tell me about {clean_query(query)} and show in {top_format}
            (if requested to show in any visual display except "textual display"
            , at the end of the response, give me a google.visualization.arrayToDataTable array in descending order representing the data, numerical data preffered,
            and don't include the code, just a string representation of the array in this section 

            Example Response:
            "blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah
            blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah
            **Google.Visualization.ArrayToDataTable string representation:**
            [["Movie", "Rating"], ["Tár", 92], ["The Banshees of Inisherin", 88], ["Women Talking", 85], ["She Said", 83], ["The Fabelmans", 81]]"
    """
    result = model.generate_content(input_list + [prompt])
    result = result.text

    return process_response(result, top_format)

def separate_response(result, format, lstopper, rstopper):
    end_index = result.find("Google.Visualization.Array")
    if end_index == -1:
        end_index = result.find(lstopper)
    else:
        end_index = result.rfind("\n", 0, end_index+1)
    
    if format == "table" and end_index != -1:
        textual_response = result[:result.find(lstopper)]
        data_response = result[result.find(lstopper) + 1:result.rfind(rstopper)]
        print(data_response)
    elif end_index != -1:
        textual_response = result[:end_index]
        data_response = result[result.find(lstopper):result.rfind(rstopper) + 1]
    else:
        textual_response = result
        data_response = None
    return textual_response, data_response

def parse_to_table(data_response):
    if data_response:
        rows = data_response.split("|\n|")
        table = [[element.strip() for element in row.split("|")] for row in rows]
        del table[1]
        table = [[item for item in row if re.search(r'\w', item)] for row in table]
        print(table)
        table = json.dumps(table)
        return table
    else:
        return None

def process_response(result, top_format):
    if top_format == "table":
        try:
            textual_response, data_response = separate_response(result, top_format, "|", "|")
            data_response = parse_to_table(data_response)
        except:
            textual_response, data_response = separate_response(result, top_format, "[", "]")   
    else:        
        textual_response, data_response = separate_response(result, top_format, "[", "]")
        if top_format == "textual display":
            data_response = None

    top_format = top_format if textual_response and data_response else "textual display"
    return textual_response, data_response, top_format