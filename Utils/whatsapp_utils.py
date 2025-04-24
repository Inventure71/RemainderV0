from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# --- Setup Chrome with your profile so you stay logged in ---
options = Options()
options.add_argument("--user-data-dir=chrome-data")
driver = webdriver.Chrome(service=Service(), options=options)
wait = WebDriverWait(driver, 60)

driver.get("https://web.whatsapp.com")

# --- 1) Wait until the main UI is ready (search box appears) ---
print("Waiting for WhatsApp Web to load and for you to scan the QR code if needed…")
search_box = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")))

# --- 2) Open your chat by its exact title ---
chat_name = "Me"
search_box.clear()
search_box.send_keys(chat_name)
time.sleep(2)
wait.until(EC.element_to_be_clickable(
    (By.XPATH, f"//span[@title='{chat_name}']"))).click()

# --- 3) Wait until at least one message is visible in the panel ---
panel = wait.until(EC.presence_of_element_located(
    (By.CSS_SELECTOR, "div.copyable-area")))
wait.until(EC.presence_of_element_located(
    (By.CSS_SELECTOR, "div.message-in, div.message-out")))

# --- Utility: close any modal or banner that might steal focus ---
def close_popups():
    for txt in ("Close", "Got it", "OK", "Dismiss"):
        try:
            btn = driver.find_element(By.XPATH, f"//button[contains(.,'{txt}')]")
            btn.click()
            time.sleep(0.3)
        except:
            pass

# --- Scrape into a set to dedupe ---
messages = set()
def scrape():
    close_popups()
    for e in driver.find_elements(By.CSS_SELECTOR, "div.message-in, div.message-out"):
        try:
            txt = e.find_element(By.CSS_SELECTOR, "span.selectable-text span").text
            if txt:
                messages.add(txt)
        except:
            continue

# --- 4) Scroll up via JS until no new messages load AND at least min_scrolls ---
min_scrolls = 50
max_scrolls = 500   # safety cap to avoid infinite loops
scroll_count = 0
last_count = -1

while scroll_count < max_scrolls:
    scrape()
    driver.execute_script("arguments[0].scrollTop = 0;", panel)
    time.sleep(1)  # allow load
    scroll_count += 1

    # after we've done the minimum, check if we're actually loading new messages
    if scroll_count >= min_scrolls:
        if len(messages) == last_count:
            print(f"No new messages after {scroll_count} scrolls, stopping early.")
            break

    last_count = len(messages)

print(f"Performed {scroll_count} scrolls, collected {len(messages)} unique messages.\n")

# --- 5) Output all unique messages ---
for i, m in enumerate(sorted(messages), 1):
    print(f"{i:03d}: {m}")

driver.quit()
