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

async def fetch_page_async(session, i, scraping_run_id, proxies, user_agents, indices, semaphore, proxy_locks):
    #await asyncio.sleep(np.random.uniform(0, 0.1))
    proxy = proxies[i % len(proxies)]
    async with proxy_locks[proxy]:
        url = f'{base_url}{str(indices[i])}?scraping_run_id={scraping_run_id}'
        headers = {"User-Agent": random.choice(user_agents), "Accept-Encoding": "gzip, deflate"}
        max_retries = 20
        for attempt in range(max_retries):
            try:
                async with semaphore:
                    #await asyncio.sleep(random.uniform(1, 2)*(active_tasks+1)/150)  # Random delay to avoid being blocked
                    async with session.get(url, proxy=proxy, headers=headers) as response:
                        if response.status == 200:
                            print(f"Page {i}. Vehicle {indices[i]} scraped...")
                            
                            html = await response.text()
                            soup = HTMLParser(html)
                            price_tag = soup.css_first('p.price')
                            year_tag = soup.css_first('p.year')
                            make_tag = soup.css_first('h2.title')
                            
                            price = int(price_tag.text().strip().removeprefix("Price: $")) if price_tag else None
                            year = int(year_tag.text().strip().removeprefix("Year: ")) if year_tag else None
                            car_make = str(make_tag.text().strip().split(",")[0]) if make_tag else ""
                            # if "Class:" in car_class:
                            #     car_class = ""
                            return price, year, car_make
                        
                        if response.status == 429:
                            print(f"Error {response.reason}. Retrying...")
                            backoff = min(5, 0.5 * (2 ** attempt)) + random.uniform(0, 0.3)
                            await asyncio.sleep(backoff)  # Wait for a random time before retrying
                            #semaphore.release() # Release the semaphore if the request fails
                            #return await fetch_page_async(session, i, scraping_run_id, proxies, user_agents, indices, semaphore)
                        
                        else:
                            print(f"Failed to retrieve page {i}: {response.status}")
                            #semaphore.release() # Release the semaphore if the request fails
                            #return await fetch_page_async(session, i, scraping_run_id, proxies, user_agents, indices, semaphore)
                        
            except Exception as e:
                print(f"Error fetching page {i}: {e}")
                #semaphore.release() # Release the semaphore if the request fails
                #return await fetch_page_async(session, i, scraping_run_id, proxies, user_agents, indices, semaphore) #None, None, None
                
        print(f"Max retries reached for page {i}. Skipping...")
        return None, None, None
            
            
async def scrape_async(limit, scraping_run_id):
    proxies = [
            "http://pingproxies:scrapemequickly@194.87.135.1:9875",
            "http://pingproxies:scrapemequickly@194.87.135.2:9875",
            "http://pingproxies:scrapemequickly@194.87.135.3:9875",
            "http://pingproxies:scrapemequickly@194.87.135.4:9875",
            "http://pingproxies:scrapemequickly@194.87.135.5:9875"
            ]
    proxy_locks = {proxy: asyncio.Lock() for proxy in proxies}
    user_agents = [
        # Windows Browsers
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.48 Safari/537.36",

    # macOS Browsers
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/91.0",

    # Linux Browsers
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",

    # Mobile Browsers
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36",

    # Older Browsers
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36",
    ]
    indices = list(range(limit))
    random.shuffle(indices)  # Shuffle the indices to randomize the scraping order
    
    proxy_concurrency = 8  # Depends on the proxy provider
    semaphore = asyncio.Semaphore(len(proxies) * proxy_concurrency)
    
    connector = aiohttp.TCPConnector(limit=100, ssl=False)  # Tune 'limit'
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(limit):
            delay = np.random.exponential(scale=0.01) 
            await asyncio.sleep(delay)  # Random delay to avoid being blocked
            task = asyncio.create_task(fetch_page_async(session, i, scraping_run_id, proxies, user_agents, indices, semaphore, proxy_locks))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
    # Process results
    prices, years, makes = zip(*[(p, y, c) for p, y, c, in results if p is not None])

    return np.array(prices), np.array(years), np.array(makes)


limit = 25000
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