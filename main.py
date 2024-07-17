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
import spacy
from argon2 import PasswordHasher
import requests

model = genai.GenerativeModel("gemini-1.5-flash")
ph = PasswordHasher()
USER_DATA = "user_data.db"
nlp = spacy.load('en_core_web_sm')

#python
import time
from datetime import datetime, timedelta
import os
import re
import sqlite3
import asyncio
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor, as_completed

#my lib
from dropbox_refresh import refresh_access_token

STOP_WORDS = ["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", 
              "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", 
              "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
              "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
                "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", 
                "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through",
                "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", 
                "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", 
                "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", 
                "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"]
UNWANTED_WORDS = [
    "Advertisement", "advertisement", "ads", "Ad", "ad", "Buy our product", "Buy now", "Shop now", 
    "Click here", "Subscribe", "Sign up", "Join now", "Limited offer", "Sale", "Discount", "Promo", 
    "Deal", "Coupon", "Exclusive offer", "Special offer", "Free trial", "Get your free", "Order now", 
    "Hurry up", "Offer ends soon", "Best price", "Save money", "Use code", "Powered by", "Sponsored by",
    "We use cookies", "cookie policy", "cookies to improve", "cookies for better experience", 
    "cookie settings", "cookie consent", "accept cookies", "This site uses cookies", "privacy policy", 
    "terms of service", "terms and conditions", "Read more", "Learn more", "More info", 
    "advertising purposes", "Third-party cookies", "ad choices"
]

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
    driver.get("https://www.google.com")
    search_bar = driver.find_element(By.NAME, "q")
    search_bar.clear()
    search_bar.send_keys(query)
    search_bar.send_keys(Keys.RETURN)

    titles = WebDriverWait(driver, 5).until(lambda driver: driver.find_elements(By.CSS_SELECTOR, "#search h3"))
    titles = [title for title in titles if "".join(title.text.split())]
    links = [title.find_element(By.XPATH, "./..") for title in titles]
    links = [link.get_attribute("href") for link in links]

    driver.quit()
    return links

def simplify_sentence(text):
    doc = nlp(text)
    normalized_tokens = []
    
    for token in doc:
        if token.text not in STOP_WORDS:
            if token.pos_ == 'VERB':
                normalized_tokens.append(token.lemma_)
            elif token.pos_ == 'NOUN':
                normalized_tokens.append(token.lemma_) 
            else:
                normalized_tokens.append(token.text) 
    
    return ' '.join(normalized_tokens)

def clean_data(text):
    text = re.sub("\W", " ", text)
    pattern = re.compile("|".join(map(re.escape, UNWANTED_WORDS)))
    text = pattern.sub("", text)
    text = simplify_sentence(text)
    return text

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
    input_list = split_long_string(input_list, 10000)
    
    query = "Using information provided above, tell me about " + query
    result = model.generate_content(input_list + [query])
    return result.text