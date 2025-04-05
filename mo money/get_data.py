import yfinance as yf
import pandas as pd

tickers = [
    "AAPL",  # Apple Inc.
    "MSFT",  # Microsoft Corp.
    "JNJ",   # Johnson & Johnson
    "PG",    # Procter & Gamble Co.
    "XOM",   # Exxon Mobil Corp.
    "KO",    # Coca-Cola Co.
    "PEP",   # PepsiCo, Inc.
    "MCD",   # McDonald's Corporation
    "PFE",   # Pfizer Inc.
    "MRK",   # Merck & Co., Inc.
    "INTC",  # Intel Corporation
    "JCI",   # Johnson Controls International
    "HD",    # Home Depot, Inc.
    "CVX",   # Chevron Corporation
    "WMT",   # Walmart Inc.
    "DIS",   # The Walt Disney Company
    "IBM",   # International Business Machines
    "T",     # AT&T Inc.
    "GE",    # General Electric Company
    "UNH",   # UnitedHealth Group
    "ADBE",  # Adobe Inc.
    "CSCO",  # Cisco Systems, Inc.
    "BA",    # Boeing Co.
    "CAT",   # Caterpillar Inc.
    "GS",    # Goldman Sachs Group
    "NVDA",  # NVIDIA Corporation
    "AMZN",  # Amazon.com, Inc.
    "GOOGL", # Alphabet Inc. (Class A)
    "GOOG",  # Alphabet Inc. (Class C)
    "SPGI",  # S&P Global Inc.
]
def get_prices():
    data = yf.download(tickers, start="2005-01-01", end="2025-04-05")
    data = data["Open"]
    data.to_csv(r"C:\Users\owain\Documents\Hackathon\KMITT\mo money\historical_data.csv")

def get_sectors():
    # Create an empty list to store the data
    sector_data = []

    # Loop through each ticker
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        info = stock.info  # Get stock info
        sector = info.get('sector', 'N/A')  # Get the sector, default to 'N/A' if not found
        sector_data.append({'Ticker': ticker, 'Sector': sector})
    
    data = pd.DataFrame(sector_data)
    data.set_index('Ticker', inplace=True)
    data.to_csv(r"C:\Users\owain\Documents\Hackathon\KMITT\mo money\ticker_sector.csv")

get_prices()