import sys
import requests
import numpy as np
from bs4 import BeautifulSoup
import json
from collections import Counter
import time
import aiohttp
import asyncio
import random
import winsound
from selectolax.parser import HTMLParser

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
            
            
async def scrape_async(limit, scraping_run_id):
    global base_url
    proxies = [
            "http://pingproxies:scrapemequickly@194.87.135.1:9875",
            "http://pingproxies:scrapemequickly@194.87.135.2:9875",
            "http://pingproxies:scrapemequickly@194.87.135.3:9875",
            "http://pingproxies:scrapemequickly@194.87.135.4:9875",
            "http://pingproxies:scrapemequickly@194.87.135.5:9875"
            ]
    proxy_locks = {proxy: asyncio.Lock() for proxy in proxies}
    proxy_last_used = {proxy: 0 for proxy in proxies}
    
    async def fetch_page_async(session, i):
        proxy = proxies[i % len(proxies)]
        async with proxy_locks[proxy]:
            while time.time() - proxy_last_used[proxy] < 0.1:
                await asyncio.sleep(0.01)
            url = f'{base_url}{str(i)}?scraping_run_id={scraping_run_id}'
            headers = {"Accept-Encoding": "gzip, deflate"}
            max_retries = 20
            for attempt in range(max_retries):
                try:
                    async with session.get(url, proxy=proxy, headers=headers) as response:
                        if response.status == 200:
                            print(f"Page {i}. scraped...")
                            
                            html = await response.text()
                            soup = HTMLParser(html)
                            price_tag = soup.css_first('p.price')
                            year_tag = soup.css_first('p.year')
                            make_tag = soup.css_first('h2.title')
                            
                            price = int(price_tag.text().strip().removeprefix("Price: $")) if price_tag else None
                            year = int(year_tag.text().strip().removeprefix("Year: ")) if year_tag else None
                            car_make = str(make_tag.text().strip().split(",")[0]) if make_tag else ""

                            return price, year, car_make
                        
                        if response.status == 429:
                            print(f"Error {response.reason}. Retrying...")
                            await asyncio.sleep(0.1)
                        
                        else:
                            print(f"Failed to retrieve page {i}: {response.status}")
                            
                except Exception as e:
                    print(f"Error fetching page {i}: {e}")
                    
                finally:
                    proxy_last_used[proxy] = time.time()
                    
            print(f"Max retries reached for page {i}. Skipping...")
            return None, None, None

    connector = aiohttp.TCPConnector(limit=200, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(limit):
            task = asyncio.create_task(fetch_page_async(session, i))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
    # Process results
    prices, years, makes = zip(*[(p, y, c) for p, y, c, in results if p is not None])

    return np.array(prices), np.array(years), np.array(makes)


limit = 2500
team_id = "1d1e0f7d-1210-11f0-a3df-0242ac120003"
base_url = 'https://scrapemequickly.com/cars/static/'
Test = True

st = time.time()
scraping_run_id = "89d5dca4-0a34-11f0-b686-4a33b21d14f6" if Test else start_scraping_run(team_id)

prices, years, makes = asyncio.run(scrape_async(limit, scraping_run_id))
if Test:
    print(prices[:10], "Size:", len(prices))
    print(years[:10] , "Size:", len(years))
    print(makes[:10] , "Size:", len(makes))
else:
    submit({
        "min_year": int(np.min(years[~np.isnan(years)])),
        "max_year": int(np.max(years[~np.isnan(years)])),
        "avg_price": int(np.mean(prices[~np.isnan(prices)])),
        "mode_make": Counter(makes).most_common(1)[0][0],
    }, scraping_run_id)
    print("Time taken:", time.time() - st)
    # Play sound when finished
    winsound.PlaySound('Scrape Me Quickly/fanfare.wav', winsound.SND_FILENAME)
    
print(int(np.min(years[~np.isnan(years)])), int(np.max(years[~np.isnan(years)])), int(np.mean(prices)), Counter(makes).most_common(1)[0][0])
print("Time taken:", time.time() - st)