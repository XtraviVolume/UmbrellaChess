import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import traceback

try:
    print("Testing minimal Chrome launch...")
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new") # Optional
    
    # Minimal arguments
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver_path = ChromeDriverManager().install()
    if os.path.isdir(driver_path):
        driver_path = os.path.join(driver_path, "chromedriver.exe")
        
    print(f"Driver path: {driver_path}")
    service = ChromeService(executable_path=driver_path, service_args=["--verbose"])
    
    driver = webdriver.Chrome(service=service, options=options)
    print("Chrome launched successfully!")
    driver.quit()
except Exception:
    traceback.print_exc()
