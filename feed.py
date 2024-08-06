from main import *
import logging

QUESTIONS = [
    "What is Amazon Web Service (AWS)?",
    "What is Docker and how does it work?",
    "Understanding Kubernetes for container orchestration",
    "What are the benefits of serverless architecture?",
    "What is quantum computing?",
    "How does blockchain technology work?",
    "What are the applications of augmented reality (AR)?",
    "What is the Internet of Things (IoT)?",
    "How does 5G technology work?",
    "What are the latest advancements in artificial intelligence?",
    "How is machine learning transforming industries?",
    "What are the ethical considerations in technology?",
    "How are startups disrupting traditional tech sectors?",
    "What are the impacts of automation on jobs?"
]

def crawl_google(q):
    try:
        day_tolerence = get_day_tolerence(q)
        links = search_google(q)
        links = [link for link in links if link is not None]
        result = iter_result(links, day_tolerence)
    except:
        logging.error("An error occurred", exc_info=True)

def crawl_brit(q):
    try:
        day_tolerence = get_day_tolerence(q)
        links = search_brit(q)
        links = [link for link in links if link is not None]
        links = list(set(links))
        result = iter_result(links, day_tolerence)
    except:
        logging.error("An error occured", exc_info=True)

if __name__ == "__main__":
    with open("questions.txt", "r") as f:
        questions = f.readlines()
    
    if not questions:
        questions = QUESTIONS
    for q in questions:
        try:
            crawl_google(q)
            crawl_brit(q)
            print(f"'{q}' is completed")
        except:
            continue
    """    query = "What is Amazon Web Service (AWS)"
    driver = init_webdriver()
    temp_query = clean_query(query).replace(" ", "+")
    driver.get("https://www.britannica.com/search?query=" + temp_query)

    links = WebDriverWait(driver, 5).until(lambda dirver: driver.find_elements(By.CSS_SELECTOR, "#content > div > div.grid > div > ul > li > a"))
    links = [link.get_attribute("href") for link in links]
    print(links)"""