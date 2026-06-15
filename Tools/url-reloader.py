import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

def reload_profile_with_chromium(url, iterations):
    print(f"Initializing Headless Chrome workflow for {url}...\n")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Uses the updated, stable headless engine
    options.add_argument("--no-sandbox")  
    options.add_argument("--disable-dev-shm-usage")  
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Explicitly telling Selenium to target your main Chrome install path
    options.binary_location = "/usr/bin/google-chrome"

    # Leaving Service empty allows Selenium's native manager to auto-pair the driver
    service = Service()

    for i in range(1, iterations + 1):
        delay = 3.0 + random.uniform(0.05, 2.0)
        driver = None
        try:
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            
            # Allow the browser context to settle and let GitHub Camo resolve metrics
            time.sleep(3)
            
            print(f"[{i}/{iterations}] Loaded profile successfully: '{driver.title}'")
            
        except Exception as e:
            print(f"[{i}/{iterations}] Browser execution error: {e}")
            
        finally:
            if driver:
                driver.quit()
        
        if i < iterations:
            print(f"Waiting {delay:.2f}s...\n")
            time.sleep(delay)

    print("\nAll iterations processed successfully!")

if __name__ == "__main__":
    TARGET_PROFILE = ""
    TOTAL_RUNS = 405
    
    reload_profile_with_chromium(TARGET_PROFILE, TOTAL_RUNS)