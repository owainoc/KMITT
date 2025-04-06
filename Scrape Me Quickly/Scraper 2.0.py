import sys
from webbrowser import Chrome
import requests
import numpy as np
from bs4 import BeautifulSoup
import json
from collections import Counter
import time
from selectolax.parser import HTMLParser
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import asyncio
from playwright.async_api import async_playwright
from playwright.async_api import async_playwright, Error as PlaywrightError


def start_scraping_run(team_id: str) -> str:
    r = requests.post(f"https://api.scrapemequickly.com/scraping-run?team_id={team_id}")

    if r.status_code != 200:
        print(r.json())
        print("Failed to start scraping run")
        sys.exit(1)

    return r.json()["data"]["scraping_run_id"]

def submit(answers: dict, scraping_run_id: str) -> bool:
    r = requests.post(
        f"https://api.scrapemequickly.com/cars/solve?scraping_run_id={scraping_run_id}",
        data=json.dumps(answers),
        headers={"Content-Type": "application/json"}
    )

    if r.status_code != 200:
        print(r.json())
        print("Failed to submit answers")
        return False

    return True

def wait_for_more_cars(driver, previous_count, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.querySelectorAll('div.car').length") > previous_count
        )
        return True
    except TimeoutException:
        return False
    
async def block_non_essentials(route):
    if route.request.resource_type in ["image", "stylesheet", "font"]:
        await route.abort()
    else:
        await route.continue_()

import random

async def scrape():
    start_time = time.time()
    all_cars = []
    retry_limit = 5
    concurrency_limit = 20
    stagger_delay = 0.1  # seconds
    request_timeout = 0.2  # pause after sending fetch

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # Initial context just to get the token
        context = await browser.new_context()
        page = await context.new_page()
        token = None

        async def handle_response(response):
            nonlocal token
            if "get-token" in response.url and response.status == 200:
                data = await response.json()
                token = data.get("token")
                print(f"🔐 Got token: {token}")

        page.on("response", handle_response)

        await page.goto(
            f"https://scrapemequickly.com/all_cars?scraping_run_id={scraping_run_id}",
            timeout=60000,
            wait_until="domcontentloaded"
        )

        await asyncio.sleep(random.uniform(0.9, 1.1))
        await page.close()

        if not token:
            print("❌ Token not found — cannot proceed.")
            await browser.close()
            return False

        pages = [await context.new_page() for _ in range(concurrency_limit)]
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        pages_count = (limit + 24) // 25
        tasks = []
        
        async def fetch_batch(page, start, attempt=1):
            async with semaphore:
                try:
                    js = f"""
                    fetch("https://api.scrapemequickly.com/cars/test?scraping_run_id={scraping_run_id}&per_page=25&start={start}", {{
                        headers: {{
                            "Authorization": "Bearer {token}",
                            "Accept": "application/json"
                        }}
                    }})
                    .then(res => res.json())
                    .then(data => window.__carData__ = data)
                    .catch(err => window.__carData__ = {{ error: err.toString() }});
                    """

                    await page.evaluate("window.__carData__ = null")
                    await asyncio.sleep(stagger_delay * (start % concurrency_limit))  # Stagger start
                    await page.evaluate(js)
                    await asyncio.sleep(request_timeout)

                    result = await page.evaluate("window.__carData__")

                    if result and "data" in result:
                        print(f"✅ Page {start//25 + 1} success")
                        return result["data"]
                    else:
                        print(f"⚠️ Page {start//25 + 1} attempt {attempt}: Bad result: {result}")
                        if attempt < retry_limit:
                            return await fetch_batch(page, start, attempt + 1)
                        return []
                except Exception as e:
                    print(f"💥 Error on page {start//25 + 1} attempt {attempt}: {e}")
                    if attempt < retry_limit:
                        return await fetch_batch(page, start, attempt + 1)
                    return []


        indices = list(range(pages_count))
        random.shuffle(indices)  # Shuffle the indices to randomize the order of requests
        for i in range(pages_count):
            start = indices[i] * 25
            page = pages[i % len(pages)]
            tasks.append(fetch_batch(page, start))

        results = await asyncio.gather(*tasks)
        for batch in results:
            all_cars.extend(batch)

        for p in pages:
            await p.close()
        await browser.close()

        if not all_cars:
            print("🔍 No cars scraped — skipping submit.")
            return False

        years = [int(car["year"].removeprefix("Year: ")) if isinstance(car["year"], str) else int(car["year"]) for car in all_cars if "year" in car]
        prices = [int(car["price"].removeprefix("Price: $")) if isinstance(car["price"], str) else int(car["price"]) for car in all_cars if "price" in car]
        makes = [car["make"] for car in all_cars if "make" in car]

        print(f"Min Year: {int(np.min(years))}")
        print(f"Max Year: {int(np.max(years))}")
        print(f"Average Price: {int(np.mean(prices))}")
        print(f"Most Common Make: {Counter(makes).most_common(1)[0][0]}")

        Success = submit({
            "min_year": int(np.min(years)),
            "max_year": int(np.max(years)),
            "avg_price": int(np.mean(prices)),
            "mode_make": Counter(makes).most_common(1)[0][0],
        }, scraping_run_id)

        print("✅ Submitted! Time taken:", round(time.time() - start_time, 2), "seconds")
        return Success


async def scrape_legacy():
    start_time = time.time()
    
    async with async_playwright() as p:
        # Launch browser (can set headless=False to see it)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        async def handle_response(response):
            url = response.url
            if "cars" in url and response.status == 200:
                try:
                    json_data = await response.json()
                    print("🚗 Car data:", json_data)
                    # Optionally, store or return this instead of scraping the DOM
                except:
                    pass

        page.on("response", handle_response)
        
        await page.goto(base_url, timeout=60000)

        cars = []

        MAX_SCROLL_ATTEMPTS = 50
        scroll_attempt = 0
        previous_count = 0

        while scroll_attempt < MAX_SCROLL_ATTEMPTS and previous_count < limit:
            # Scroll down
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            try:
                await page.wait_for_function(
                    f"document.querySelectorAll('div.car').length > {previous_count}",
                    timeout=3000
                )
            except:
                scroll_attempt += 1
                print(f"No new cars (attempt {scroll_attempt})")
                continue

            # Count car divs
            cars_now = await page.eval_on_selector_all("div.car", "els => els.length")

            if cars_now > previous_count:
                new_cars = await page.evaluate("""
                    () => {
                        let cars = [];
                        document.querySelectorAll('div.car:not(.processed)').forEach(car => {
                            let make = car.querySelector('h2.title')?.innerText.split(',')[0] || '';
                            let year = car.querySelector('p.year')?.innerText.replace('Year:', '').trim() || '';
                            let price = car.querySelector('p.price')?.innerText.replace('Price: $', '').trim() || '';
                            cars.push({ make, year, price });
                            car.classList.add('processed');
                        });
                        return cars;
                    }
                """)

                cars.extend([
                    {
                        "make": str(car["make"]),
                        "year": int(car["year"]) if car["year"] else None,
                        "price": float(car["price"]) if car["price"] else None
                    }
                    for car in new_cars
                ])
                
                previous_count = cars_now
                scroll_attempt = 0
                print(f"Loaded {cars_now} cars...")
            else:
                scroll_attempt += 1
                print(f"No new cars (attempt {scroll_attempt})")

        Success = submit({
            "min_year": int(np.min(cars["year"])),
            "max_year": int(np.max(cars["year"])),
            "avg_price": int(np.mean(cars["price"])),
            "mode_make": Counter(cars["make"]).most_common(1)[0][0],
        }, scraping_run_id)
        print("Time taken:", time.time() - start_time)
        
        await browser.close()
        return Success
    
    # # Set up Chrome
    # options = Options()
    
    # # # Initialize undetected Chrome
    # driver = webdriver.Chrome(options=options)

    # # Load the page
    # driver.get(base_url)
        
    # MAX_SCROLL_ATTEMPTS = 50
    # #SCROLL_PAUSE = 0.01

    # previous_count = 0
    # scroll_attempt = 0
    # cars = []
    
    # while scroll_attempt < MAX_SCROLL_ATTEMPTS and previous_count < limit:
    #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    #     new_cars = wait_for_more_cars(driver, previous_count)

    #     if new_cars:
    #         cars_data = driver.execute_script("""
    #             let cars = [];
    #             document.querySelectorAll('div.car:not(.processed)').forEach(car => {
    #                 let make = car.querySelector('h2.title')?.innerText.split(',')[0] || '';
    #                 let year = car.querySelector('p.year')?.innerText.replace('Year:', '').trim() || '';
    #                 let price = car.querySelector('p.price')?.innerText.replace('Price: $', '').trim() || '';
    #                 cars.push({ make, year, price });
    #                 car.classList.add('processed');
    #             });
    #             return cars;
    #         """)

    #         cars.extend([
    #             {
    #                 "make": str(car["make"]),
    #                 "year": int(car["year"]) if car["year"] else None,
    #                 "price": float(car["price"]) if car["price"] else None
    #             }
    #             for car in cars_data
    #         ])
                
    #         previous_count = driver.execute_script("return document.querySelectorAll('div.car').length")
    #         print(f"Loaded {previous_count} cars... continuing scroll.")
    #         scroll_attempt = 0  # reset attempts if new cars appeared
    #     else:
    #         scroll_attempt += 1  # no new cars? count an attempt
    #         print(f"No new cars detected (attempt {scroll_attempt}).")

    # print(f"Done scrolling. Total cars loaded: {previous_count}")

    
    # makes = [car["make"] for car in cars]
    # years = [car["year"] for car in cars]
    # prices = [car["price"] for car in cars]
    # print(makes[:5], len(makes))
    # print(years[:5], len(years))
    # print(prices[:5], len(prices))
    
    # print("Time:", time.time() - st)
    # driver.quit()

    
def main():
    st = time.time()

    print(asyncio.run(scrape()))
    


limit = 25000
team_id = "1d1e0f7d-1210-11f0-a3df-0242ac120003"
Test = False
scraping_run_id = "89d5dca4-0a34-11f0-b686-4a33b21d14f6" if Test else start_scraping_run(team_id)
base_url = f'https://scrapemequickly.com/all_cars?scraping_run_id={scraping_run_id}'
proxies = [
        "http://pingproxies:scrapemequickly@194.87.135.1:9875",
        "http://pingproxies:scrapemequickly@194.87.135.2:9875",
        "http://pingproxies:scrapemequickly@194.87.135.3:9875",
        "http://pingproxies:scrapemequickly@194.87.135.4:9875",
        "http://pingproxies:scrapemequickly@194.87.135.5:9875"
        ]

if Test:
    limit = 2500
if __name__ == "__main__":
    main()