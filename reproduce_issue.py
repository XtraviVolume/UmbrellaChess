import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import traceback

try:
    print("Testing Chrome launch WITH gui.py options...")
    options = webdriver.ChromeOptions()
    
    # Options from gui.py
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('useAutomationExtension', False)
    # Duplicate line from gui.py purposely included to match
    options.add_experimental_option('useAutomationExtension', False)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming this script is in same dir as gui.py would be (d:\UmbrellaChess\PawnBit-main)
    # gui.py creates profile in os.path.dirname(script_dir) + chrome_profile_new. 
    # But gui.py is in src/, so os.path.dirname(src) is root.
    # checking where I put this file: D:\UmbrellaChess\PawnBit-main\reproduce_issue.py
    # So I should use the same profile path logic as gui.py
    
    request_dir = r"D:\UmbrellaChess\PawnBit-main"
    user_data_dir = os.path.join(request_dir, "chrome_profile_new")
    
    print(f"[DEBUG] User Data Dir: {user_data_dir}")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.page_load_strategy = 'eager'
    
    print("[DEBUG] Installing/Finding ChromeDriver...")
    driver_path = ChromeDriverManager().install()
    print(f"[DEBUG] Driver Path: {driver_path}")
    
    if os.path.isdir(driver_path):
        chromedriver_path = os.path.join(driver_path, "chromedriver.exe")
    else:
        chromedriver_path = driver_path
        
    print("[DEBUG] Starting Chrome Driver Service...")
    service = ChromeService(executable_path=chromedriver_path, service_args=["--verbose"])
    
    driver = webdriver.Chrome(service=service, options=options)
    print("Chrome launched successfully with GUI options!")
    driver.quit()
    
except Exception as e:
    print("--- REPRODUCTION ERROR ---")
    traceback.print_exc()
