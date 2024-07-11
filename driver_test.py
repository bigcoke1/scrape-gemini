from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def init_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-background-timer-throttling")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(120)
    driver.set_script_timeout(120)
    return driver

driver = init_webdriver()
driver.get("https://www.google.com")
print("Page Title is:", driver.title)
driver.quit()
