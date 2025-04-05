import yfinance as yf
import pandas as pd
import datetime as dt
import numpy as np


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
    initial_price = data_start["Open"].to_numpy()
    returns = (data_end["Close"].to_numpy() - initial_price) / initial_price
    return np.concatenate((returns, initial_price))

# tickers = ["AAPL", "KO", "JPM"]
# period = get_dates("2023-05-02", "2024-08-03")
# print(get_prices(tickers, period))
ticker = yf.Ticker("KO")
print(ticker.info)
