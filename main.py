import pandas as pd
import numpy as np
import os
from glob import glob
from datetime import date
from pandas._libs.tslibs import NaT
from pandas.core.indexes.datetimes import date_range
import yfinance as yf
from matplotlib import pyplot as plt
from functions import *

# Potential problems: 
# does not take into account non-trade fees (Stake Black).
# NZ and US dates are taken at face value.
# NZD cash held in sharesies is not counted as portfolio value but Hatch and Stake cash is counted.
# Buy orders before stock splits.


# Controls which data should be read
hatch = True
stake = True
sharesies = True

tradesArray = []
depositsArray = []

# Reads in data from Hatch.
if hatch:
    
    hatchTrades, hatchDeposits = hatchRead()
    tradesArray.append(hatchTrades)
    depositsArray.append(hatchDeposits)

# Reads in data from Stake.
if stake:
    
    stakeTrades, stakeDeposits = stakeRead()
    tradesArray.append(stakeTrades)
    depositsArray.append(stakeDeposits)

# Reads in trades from Sharesies. 
if sharesies:

    sharesiesTrades, sharesiesDeposits = sharesiesRead()
    tradesArray.append(sharesiesTrades)
    depositsArray.append(sharesiesDeposits)
    

# Combining dataframes.
trades = pd.concat(tradesArray, ignore_index=True)
trades['Trade Date'] = pd.to_datetime(trades['Trade Date'])
deposits = pd.concat(depositsArray, ignore_index=True)
deposits['Date'] = pd.to_datetime(deposits['Date'], dayfirst=True)


# Finding the min date.
fromDate = deposits['Date'].min() if deposits['Date'].min() < trades['Trade Date'].min() else trades['Trade Date'].min()
# Finding today's date.
todayDate = date.today()


# Splitting trades into tradesUS and tradesNZ.
tradesUS = trades[trades['Currency'] == 'USD'].copy()
tradesNZ = trades[trades['Currency'] == 'NZD'].copy()


# Imports USD exchange data.
adjCloseUSD = yf.download('NZDUSD=X', start=fromDate, endDate=todayDate)['Adj Close']
# Imports NZD exchange data.
adjCloseNZD = yf.download('USDNZD=X', start=fromDate, endDate=todayDate)['Adj Close']


# Finds the initial investment on NZ stocks over time.
NZDinvestedNZstocks = initialInvest(tradesNZ, fromDate, todayDate)

# Dataframe containing information about USD held over time
USDCash = USDOverTime(deposits, fromDate, todayDate, tradesUS)


# Forming ticker strings to pass to yf.download() 
tickersUS = stockStringBuilder(tradesUS['Ticker'])
tickersNZ = stockStringBuilder(tradesNZ['Ticker'])


# Imports data for US stocks
adjCloseDataUS = yf.download(tickersUS, start=fromDate, end=todayDate)['Adj Close']
# Imports data for NZ stocks
adjCloseDataNZ = yf.download(tickersNZ, start=fromDate, end=todayDate)['Adj Close']


# Forms quantity over time dataframe for all stocks.
unitsDataUS = unitsOverTime(tradesUS, adjCloseDataUS)
unitsDataNZ = unitsOverTime(tradesNZ, adjCloseDataNZ)

# Calculating values of investments in respective currencies
# For US stocks.
investedStockValUS = unitsDataUS * adjCloseDataUS
investedStockValUS['USD stock value'] = investedStockValUS.sum(axis=1)
# For NZ stocks.
investedStockValNZ = unitsDataNZ * adjCloseDataNZ
investedStockValNZ['NZD stock value'] = investedStockValNZ.sum(axis=1)


# forward filling investedStockVal and forex data with missing values.
investedStockValUS = investedStockValUS.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
investedStockValNZ = investedStockValNZ.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
adjCloseNZD = adjCloseNZD.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
adjCloseUSD = adjCloseUSD.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
USDCash = USDCash.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')


# Creating infoUSD dataframe containing summarised important information in USD about US stocks.
infoUSDstockUS = pd.DataFrame(index=investedStockValUS.index)
infoUSDstockUS['Total value of investment'] = investedStockValUS['USD stock value'].add(USDCash['USD cash held'])
infoUSDstockUS['Total initial investment'] = USDCash['initial USD bought']
infoUSDstockUS['Profit/Loss'] = infoUSDstockUS['Total value of investment'].sub(infoUSDstockUS['Total initial investment'])


# Creating infoNZD dataframe containing summarised important information in NZD about US stocks.
infoNZDStockUS = pd.DataFrame(index=investedStockValUS.index)
infoNZDStockUS['Total value of investment'] = infoUSDstockUS['Total value of investment'] * adjCloseNZD
infoNZDStockUS['Total initial investment'] = USDCash['NZD invested in USD']
infoNZDStockUS['Profit/Loss'] = infoNZDStockUS['Total value of investment'].sub(infoNZDStockUS['Total initial investment'])


# Creating infoNZDstockNZ dataframe containing summarised important information in NZD about NZ stocks.
infoNZDStockNZ = pd.DataFrame(index=date_range(fromDate, todayDate))
infoNZDStockNZ['Total value of investment'] = investedStockValNZ['NZD stock value']
infoNZDStockNZ['Total initial investment'] = NZDinvestedNZstocks
infoNZDStockNZ['Profit/Loss'] = infoNZDStockNZ['Total value of investment'] - infoNZDStockNZ['Total initial investment']

# Creating overall_NZD dataframe containined summarised information about all stocks.
infoOverall_NZD = pd.DataFrame(index=date_range(fromDate, todayDate))
infoOverall_NZD['Total value of investment'] = infoNZDStockNZ['Total value of investment'] \
                                            + infoNZDStockUS['Total value of investment']
infoOverall_NZD['Total initial investment'] = infoNZDStockNZ['Total initial investment'] \
                                            + infoNZDStockUS['Total initial investment']
infoOverall_NZD['Profit/Loss'] = infoNZDStockNZ['Profit/Loss'] \
                                + infoNZDStockUS['Profit/Loss']
infoOverall_NZD['% Profit/Loss'] = infoOverall_NZD['Profit/Loss'] / infoOverall_NZD['Total initial investment'] * 100



# Forming plot.
fig, ax = plt.subplots(3)
fig.suptitle('Portfolio Tracker ($NZD)')

ax[0].plot(infoOverall_NZD.index, infoOverall_NZD['Total value of investment'], 'g-', label='Portfolio value ($NZD)')
ax[0].plot(infoOverall_NZD.index, infoOverall_NZD['Total initial investment'], 'b-', label='My contribution ($NZD)')

ax[1].plot(infoOverall_NZD.index, infoOverall_NZD['Profit/Loss'], 'r-', label='Profit/Loss ($NZD)')

ax[2].plot(infoOverall_NZD.index, infoOverall_NZD['% Profit/Loss'], 'k-', label='% Profit/Loss')

for i in range(3):
    ax[i].legend()
    ax[i].grid(axis='y', which='both')


# Displaying summarised current information:
print(f"The current porfolio value is ${infoOverall_NZD.loc[str(todayDate), 'Total value of investment']:.2f}.")
print(f"The initial investment value is ${infoOverall_NZD.loc[str(todayDate), 'Total initial investment']:.2f}.")
print(f"The current Profit/Loss is ${infoOverall_NZD.loc[str(todayDate), 'Profit/Loss']:.2f}.")
print(f"The current % Profit/Loss is {infoOverall_NZD.loc[str(todayDate), '% Profit/Loss']:.2f}%.")

plt.show()