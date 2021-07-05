import pandas as pd
import numpy as np
import os
from glob import glob
from datetime import date
from pandas._libs.tslibs import NaT
import yfinance as yf




# Reads in trades from hatch as pandas dataframe
hatchFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + '*.csv')
hatchTrades = pd.read_csv(hatchFilePath[0])


# Reads in trades from Stake as pandasdataframe 
stakeFilePath = glob('trade reports' + os.sep + 'stake' + os.sep + '*.xlsx')
stakeTrades = pd.read_excel(stakeFilePath[0], sheet_name='Trades')


# Reads in trades from Sharesies 
# UNDER CONSTRUCTION


# Simplifying hatchTrades dataframe.
hatchTrades = hatchTrades.assign(Fees=3) # Forms a new column containing the flat $3 fee for each trade.
hatchTrades = hatchTrades.drop(['Comments'], axis=1) # Removes the comments column.
hatchTrades = hatchTrades.rename({'Instrument Code' : 'Ticker', 'Transaction Type' : 'Type'}, axis=1)
# hatchTrades['Trade Date'] = pd.to_datetime(hatchTrades['Trade Date'], format = '%d%M%Y')

# Simplifying stakeTrades dataframe.
# Removing useless data:
stakeTrades = stakeTrades.drop(['DATE (US)', 'REFERENCE', 'TAF FEE (USD)', 'SEC FEE (USD)', 'VALUE (USD)',
                                'FX RATE', 'LOCAL CURRENCY VALUE'], axis=1) 
# Renaming data to match the hatchTrades convention:
stakeTrades = stakeTrades.rename({'SETTLEMENT DATE (US)' : 'Trade Date', 'SIDE' : 'Type', 
                                'UNITS' : 'Quantity', 'EFFECTIVE PRICE (USD)' : 'Price', 
                                'BROKERAGE FEE (USD)' : 'Fees', 'SYMBOL' : 'Ticker'}, axis=1) 
# Reassigning B/S values in Type to BUY/SELL to match hatch convention:
stakeTrades['Type'] = np.where(stakeTrades['Type'] == 'B', 'BUY', 'SELL')
# stakeTrades['Trade Date'] = pd.to_datetime(stakeTrades['Trade Date'], format = '%Y%M%d')


# Combining dataframes
trades = pd.concat([hatchTrades, stakeTrades], ignore_index=True)
# Making Trade date be stored as datetime.
trades['Trade Date'] = pd.to_datetime(trades['Trade Date'])

# Finding the min date.
fromDate = trades['Trade Date'].min()

# Finding today's date.
todayDate = date.today()


# Building string parameter to pass to yf.download containing all tickers.
# Unique stocks:
uniqueStocks = trades['Ticker'].unique()
# Building string:
tickers = uniqueStocks[0]
for stock in range(1, len(uniqueStocks)):
    tickers += ' ' + uniqueStocks[stock]

# Imports data
adjCloseData = yf.download(tickers, start=fromDate, end=todayDate)['Adj Close']


# Forming pandas series containing units of stock for each stock.
unitsData = adjCloseData * 0
for stock in uniqueStocks:
    # Adds stock quantity from buy date to end for each buy order. Treats multiple buy orders in 1 day as 1 order.
    buyOrders = trades[(trades['Type'] == 'BUY') & (trades['Ticker'] == stock)]['Trade Date'].unique()

    for buyOrder in buyOrders:
        currentUnits = np.sum(trades[(trades['Type'] == 'BUY') & (trades['Ticker'] == stock) 
                        & (trades['Trade Date'] == buyOrder)]['Quantity'].to_numpy())
        unitsData.loc[buyOrder:][stock] += currentUnits
    
    # Substracts stock quantity from sell date to end for each sell order. Treats multiple sell orders in 1 day as 1 order.
    sellOrders = trades[(trades['Type'] == 'SELL') & (trades['Ticker'] == stock)]['Trade Date'].unique()
    for sellOrder in sellOrders:
        currentUnits = np.sum(trades[(trades['Type'] == 'SELL') & (trades['Ticker'] == stock) 
                        & (trades['Trade Date'] == sellOrder)]['Quantity'].to_numpy())
        unitsData.loc[sellOrder:][stock] -= currentUnits

investedStockVal = unitsData * adjCloseData
investedStockVal['Total'] = investedStockVal.sum(axis=1)

pass
