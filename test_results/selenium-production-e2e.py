"""Run after `python -m pip install selenium` to test the public judge demo."""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,1200")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 120)

try:
    driver.get("https://sonil15.github.io/HyLeakAI/")
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#mode-seg [data-mode='live']"))).click()
    wait.until(lambda d: d.find_element(By.ID, "live-simulation").is_enabled())
    wait.until(lambda d: d.find_element(By.ID, "run-live").is_enabled())
    fault_count = driver.find_element(By.ID, "live-fault-count")
    fault_count.clear()
    fault_count.send_keys("3")
    driver.find_element(By.ID, "run-live").click()
    wait.until(lambda d: "Live assessment complete" in d.find_element(By.ID, "live-status").text)
    assert "Live API" in driver.find_element(By.ID, "risk-source-badge").text
    assert len(driver.find_elements(By.CSS_SELECTOR, "#waterfall .wf-row")) == 3
    print("PASS: live assessment rendered in production")
finally:
    driver.quit()
