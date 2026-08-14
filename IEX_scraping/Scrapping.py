import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException

def generate_urls_for_range(start_date_str="2026-01-01", end_date_str="2026-01-31"):
    """Generates all 15-minute block URLs for each date in the specified range."""
    base_url = "https://www.iexindia.com/market-data/day-ahead-market/aggregate-demand-supply"
    dates = pd.date_range(start=start_date_str, end=end_date_str)
    urls = []

    for dt in dates:
        formatted_date = dt.strftime("%d-%m-%Y")  # Format as DD-MM-YYYY
        for h in range(24):
            for m in (0, 15, 30, 45):
                start_m = m
                start_h = h
                end_m = (m + 15) % 60
                end_h = h + 1 if end_m == 0 else h
                
                from_time = f"{start_h:02d}%3A{start_m:02d}-{end_h:02d}%3A{end_m:02d}"
                url = f"{base_url}?date={formatted_date}&fromTime={from_time}&toTime=23%3A45-24%3A00"
                urls.append((formatted_date, url))
                
    return urls

# Configure Chrome Driver
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
# options.add_argument("--headless")  # Uncomment to run without browser window

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

all_extracted_records = []
target_urls = generate_urls_for_range("2026-01-02", "2026-01-31")

try:
    for idx, (current_date, url) in enumerate(target_urls, 1):
        print(f"[{idx}/{len(target_urls)}] Scraping Date: {current_date} | URL: {url}")
        driver.get(url)
        
        while True:
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//table//tbody/tr")))
            except TimeoutException:
                print(f"  No data found for {current_date}")
                break

            rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
            if not rows:
                break
                
            first_row_before = rows[0]

            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 4:
                    all_extracted_records.append({
                        "Date": current_date,
                        "Source URL": url,
                        "Time Block": cols[0].text.strip(),
                        "Price (in Rs./MWh)": cols[1].text.strip(),
                        "Buy / Demand (in MW)": cols[2].text.strip(),
                        "Sell / Supply (in MW)": cols[3].text.strip()
                    })

            # Pagination handling
            try:
                next_button = driver.find_element(
                    By.XPATH, 
                    "//li[contains(@class, 'next') and not(contains(@class, 'disabled'))]/a | "
                    "//button[contains(@aria-label, 'Next') and not(@disabled)] | "
                    "//a[contains(@class, 'page-link') and (text()='›' or contains(text(), 'Next'))]"
                )

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                
                try:
                    next_button.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", next_button)

                wait.until(EC.staleness_of(first_row_before))

            except (NoSuchElementException, TimeoutException):
                break

finally:
    driver.quit()

# Export combined dataset to CSV
df = pd.DataFrame(all_extracted_records)
df.to_csv("iex_demand_supply_jan_2_to_31_2026.csv", index=False)
print(f"\nProcessing finished. Total records captured: {len(df)}")
