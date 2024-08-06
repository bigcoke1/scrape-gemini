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
    return text

def get_date():
    current_datetime = datetime.now()
    format_string = "%m-%d-%y"
    current_datetime = current_datetime.strftime(format_string)

    return current_datetime

def get_day_tolerence(query):
    prompt = f"""according to the following prompt, tell me how recent does the data need to be to answer the question with good accuracy,
             and convert the time to datetime format, and today's date is {get_date()}
            prompt: {query}.
            reply with nothing else, but the number to indicate how many days (If the data freshness is not critical, reply with a large number like 3650)"""
    day_tolerence = model.generate_content(prompt)
    day_tolerence = day_tolerence.text
    day_tolerence = ''.join(re.findall(r'\d+', day_tolerence))
    print(f"how recent does the data need to be: {day_tolerence.strip()} days")
    return float(day_tolerence)

def compare_date(date, day_tolerence):
    date = datetime.strptime(date, "%m-%d-%y").date()
    return abs(date - datetime.now().date()) < timedelta(days=day_tolerence)

def get_local_path(id, date):
    data_folder = "data"
    path = str(id) + "-" + date + ".pickle"
    path = os.path.join(data_folder, path)

    return path

def collect_result(link, day_tolerence, recursion_depth=0, max_recursion_depth=3):
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
            if webpage: #if the entry was found but is too old
                print("old file detected and deleted")
                cur.execute("DELETE FROM webpage WHERE url = ?", [link])
                path = get_local_path(webpage[0], webpage[1])
                try:
                    os.remove(path)
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
                    text = collect_result(link, day_tolerence, recursion_depth + 1, max_recursion_depth)
                else:
                    print("Max recursion depth reached. Aborting.")
    con.close()
    return text

def iter_result(links, day_tolerence):
    result = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(lambda l: collect_result(l, day_tolerence), link): link for link in links}
        for future in as_completed(futures):
            try:
                result.append(future.result())
            except Exception as exc:
                print(f"An error occurred: {exc}")
    print(f"{len(result)} elements in result")
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

def get_AI_response(query, input_list):
    prompt_format = """
        Give me a JSON (and only the JSON enclosed with '{}' with no explanation) of what type of visual display the user is asking 
        (i.e. bar graph, pie chart, scatterplot, line graph, histogram, table, textual display, area chart, bubble chart, 
        histogram, geo chart, donut chart, and gauge chart)
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
    
    if top_format != "textual display":
        prompt = f"""Using information provided above, tell me about {clean_query(query)} in JSON format (and only the JSON enclosed with curly brackets with no explanation)
                Using this JSON schema:
                    Response = {{
                        "textual_response": "str",
                        "data_response": "str"
                    }}
                (data_response is a google.visualization.arrayToDataTable array in descending order if it involves ranking or ascending order if it involves time, numerical data preffered,
                and don't include the code, just a string representation of the array in this section 

                Example Response:
                {{
                    "textual_response": "blah blah blah blah blah blah blah blah blah",
                    "data_response": "[["Movie", "Rating"], ["Tár", 92], ["The Banshees of Inisherin", 88], ["Women Talking", 85], ["She Said", 83], ["The Fabelmans", 81]]"
                }}
        """
    else:
        prompt = f"""Using information above, tell me about {clean_query(query)} in JSON format (and only the JSON enclosed with curly brackets with no explanation)
                Using this JSON schema:
                    Response = {{
                        "textual_response": "str"
                    }}
                textual response should be at least one paragraph long.
        """
    result = model.generate_content(input_list + [prompt])
    result = result.text
    result = result[result.find("{"):result.rfind("}") + 1]
    result = json.loads(result)
    textual_response, data_response = result.get("textual_response"), result.get("data_response")
    top_format = top_format if textual_response and data_response else "textual display"
    textual_response = markdown.markdown(textual_response, extensions=['nl2br'])
    return textual_response, data_response, top_format