import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np
import re
import json
import requests

URL = "mts-prism.com"
PORT = 8082

# Please do NOT share this information anywhere, unless you want your team to be cooked.
TEAM_API_CODE = "47c458aa60dc866b468bd090793c4e5b"
# @cyrus or @myguysai on Discord if you need an API key


def send_get_request(path):
    """
    Sends a HTTP GET request to the server.
    Returns:
        (success?, error or message)
    """
    headers = {"X-API-Code": TEAM_API_CODE}
    response = requests.get(f"http://{URL}:{PORT}/{path}", headers=headers)

    # Check whether there was an error sent from the server.
    # 200 is the HTTP Success status code, so we do not expect any
    # other response code.
    if response.status_code != 200:
        return (
            False,
            f"Error - something went wrong when requesting [CODE: {response.status_code}]: {response.text}",
        )
    return True, response.text


def send_post_request(path, data=None):
    """
    Sends a HTTP POST request to the server.
    Pass in the POST data to data, to send some message.
    Returns:
         (success?, error or message)
    """
    headers = {"X-API-Code": TEAM_API_CODE, "Content-Type": "application/json"}

    # Convert the data from python dictionary to JSON string,
    # which is the expected format to be passed
    data = json.dumps(data)
    response = requests.post(f"http://{URL}:{PORT}/{path}", data=data, headers=headers)

    # Check whether there was an error sent from the server.
    # 200 is the HTTP Success status code, so we do not expect any
    # other response code.
    if response.status_code != 200:
        return (
            False,
            f"Error - something went wrong when requesting [CODE: {response.status_code}]: {response.text}",
        )
    return True, response.text


def get_context():
    """
    Query the challenge server to request for a client to design a portfolio for.
    Returns:
        (success?, error or message)
    """
    return send_get_request("/request")


def get_my_current_information():
    """
    Query your team information.
    Returns:
        (success?, error or message)
    """
    return send_get_request("/info")


def send_portfolio(weighted_stocks):
    """
    Send portfolio stocks to the server for evaluation.
    Returns:
        (success?, error or message)
    """
    data = [
        {"ticker": weighted_stock[0], "quantity": weighted_stock[1]}
        for weighted_stock in weighted_stocks
    ]
    return send_post_request("/submit", data=data)


def get_dates(start, end):
    ticker = yf.Ticker("KO")
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)

    data_start = ticker.history(start=start, end=start + pd.Timedelta(days=3))
    data_end = ticker.history(start=end - pd.Timedelta(days=3), end=end)
    # If there's no data at all (e.g., wrong ticker), return None
    if data_start.empty or data_end.empty:
        print("ahhhh")
        return None
  
    start = data_start.index[0]
    end = data_end.index[-1]
    return start, end

def get_prices(tickers, period):
    data_start = yf.download(tickers, start=period[0], end=period[0] + pd.Timedelta(days=1))
    data_end = yf.download(tickers, start=period[1], end=period[1] + pd.Timedelta(days=1))
    # Extract Open and Close prices for each ticker
    open_prices = data_start["Open"].iloc[0]
    close_prices = data_end["Close"].iloc[0]
    # Calculate returns
    returns = (close_prices - open_prices) / open_prices

    # Build final DataFrame
    result = pd.DataFrame({
        'Initial Price': open_prices,
        'Return': returns
    })
    return result

def get_portfolio(tickers, budget, start, end, data):
    start = pd.to_datetime(start)
    end = pd.to_datetime(end)
    # Create an empty DataFrame for the results
    returns_data = pd.DataFrame(columns=["Ticker", "Starting Value", "Return"])
    price_start = data.loc[start][tickers]
    price_end = data.loc[end][tickers]
    returns = (price_end - price_start)/price_start

    returns_data = pd.DataFrame({
    "Price": price_start,
    "Return": returns
    })
    
    best5 = returns_data.nlargest(5, "Return")
    budget_split = np.array([0.4,0.2,0.1,0.05,0.05]) * budget
    port = np.zeros(5, dtype=np.int64)
    for i in range(4,-1,-1):
        port[i] = budget_split[i] // best5.iloc[i]["Price"]
        if i < 0:
            budget_split[i+1] += budget_split[i] - port[i]*best5.iloc[i]["Price"]
    return [(asset, port[i]) for i,asset in enumerate(best5.index)]


def interpret_investment_prompt(prompt, categories):
    # Extracting the information using regular expressions
    avoid_investment = re.search(r"avoids (.+?)\.", prompt).group(1).split(" and ")
    start_date = re.search(r"investment start date was (.+?)\.", prompt).group(1)
    end_date_match = re.search(r"investment end date was (.+?)\.", prompt)
    end_date = end_date_match.group(1) if end_date_match else datetime.now().strftime('%Y-%m-%d')
    budget = re.search(r"investment budget is \$(\d+)\.", prompt).group(1)
    
    # Filter the avoid_investment categories
    filtered_avoid_investment = [category for category in avoid_investment if category in categories]
    
    # Format dates to yyyy-mm-dd
    start_date = datetime.strptime(start_date, '%B %dth, %Y').strftime('%Y-%m-%d')
    if end_date_match:
        end_date = datetime.strptime(end_date, '%B %dth, %Y').strftime('%Y-%m-%d')
    
    return {
        "Avoids Investment In": filtered_avoid_investment,
        "Start": start_date,
        "End": end_date,
        "Budget": budget
    }

# Load the tickers and sectors
tickers_df = pd.read_csv(r'C:\Users\owain\Documents\Hackathon\KMITT\mo money\ticker_sector.csv')
# Load the historical data
historical_df = pd.read_csv(r"C:\Users\owain\Documents\Hackathon\KMITT\mo money\historical_data.csv", index_col=0, parse_dates=True)
# Example prompt
generated_context = "Andrew Vega is 77 years old and his investment start date was February 9th, 2016. His investment end date was July 14th, 2016. He enjoys knitting and avoids Real Estate and Construction. Their total investment budget is $49434."
prompt = "What does this person not want to invest in? " + generated_context
categories = tickers_df["Sector"].unique()

# Interpreting the prompt
investment_info = interpret_investment_prompt(prompt, categories)


# Filter the DataFrame to exclude rows with sectors in "Avoids Investment In" (case-insensitive)
remaining_tickers = tickers_df[~tickers_df['Sector'].str.lower().isin([sector.lower() for sector in investment_info['Avoids Investment In']])]['Ticker']

# Convert the filtered DataFrame column to a pandas Series
remaining_tickers = remaining_tickers.reset_index(drop=True)

portfolio = get_portfolio(remaining_tickers.tolist(), float(investment_info["Budget"]), investment_info["Start"], investment_info["End"], historical_df)
print(portfolio)

# # Save the pandas Series to a CSV file
# remaining_tickers.to_csv(r'C:\Users\owain\Documents\Hackathon\KMITT\mo money\remainingtickers.csv', index=False)
