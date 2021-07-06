import pandas as pd
import numpy as np
import os
from glob import glob
from datetime import date
from pandas._libs.tslibs import NaT
import yfinance as yf
from matplotlib import pyplot as plt

# Potential problem: does not take into account non-trade fees (Stake Black).

# Controls which data should be read
hatch = True
stake = False
sharesies = False


# Reads in trades from hatch as pandas dataframe. File format works as of 5/7/21.
if hatch:
    hatchTradeFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + 'order-transaction*.csv')
    hatchTrades = pd.read_csv(hatchTradeFilePath[0])
    # Simplifying hatchTrades dataframe.
    hatchTrades = hatchTrades.assign(Fees=3) # Forms a new column containing the flat $3 fee for each trade.
    hatchTrades = hatchTrades.drop(['Comments'], axis=1) # Removes the comments column.
    hatchTrades = hatchTrades.rename({'Instrument Code' : 'Ticker', 'Transaction Type' : 'Type'}, axis=1)

    # Reads in deposit data from Hatch
    # The .csv file to be read is manually made. Hatch does not provide any deposit information as of 5/7/21.
    hatchDepositFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + 'Hatch Deposit Data.csv')
    hatchDeposits = pd.read_csv(hatchDepositFilePath[0])    



if stake:
    # Reads in trades from Stake as pandasdataframe. File format works as of 5/7/21.
    stakeFilePath = glob('trade reports' + os.sep + 'stake' + os.sep + '*.xlsx')
    stakeTrades = pd.read_excel(stakeFilePath[0], sheet_name='Trades')
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

    # Reads in deposit data from Stake
    # The provided Stake report does not contain the NZD amounts as of 5/7/21. This needs to be added manually.
    stakeDepositFilePath = stakeFilePath
    stakeDeposits = pd.read_excel(stakeDepositFilePath[0], sheet_name='Deposits & Withdrawals')
    # Simplifying stakeDeposits dataframe:
    # Removing useless data.
    stakeDeposits = stakeDeposits.drop(['REFERENCE', 'FUNDING METHOD'], axis=1)
    # Renaming data.
    stakeDeposits = stakeDeposits.rename({'DATE (US)' : 'Date', 'FUNDING TYPE' : 'Type', 
                                        'RECEIVE AMOUNT (USD)' : 'USD Quantity'}, axis=1)



# Reads in trades from Sharesies 
# UNDER CONSTRUCTION
if sharesies:
    # Reads in trades from Sharesies.

    # Reads in deposit data from Sharesies
    # UNDER CONSTRUCTION
    pass

if hatch and stake:
    # Combining trades dataframes
    trades = pd.concat([hatchTrades, stakeTrades], ignore_index=True)
    # Making Trade date be stored as datetime.
    trades['Trade Date'] = pd.to_datetime(trades['Trade Date'])

    # Combining deposits dataframes
    deposits = pd.concat([hatchDeposits, stakeDeposits], ignore_index=True)
    # Making date be stored as datetime.
    deposits['Date'] = pd.to_datetime(deposits['Date'])

elif hatch:
    trades = hatchTrades
    # Making Trade date be stored as datetime.
    trades['Trade Date'] = pd.to_datetime(trades['Trade Date'])

    deposits = hatchDeposits
    # Making date be stored as datetime.
    deposits['Date'] = pd.to_datetime(deposits['Date'])

elif stake:
    trades = stakeTrades
    # Making Trade date be stored as datetime.
    trades['Trade Date'] = pd.to_datetime(trades['Trade Date'])

    deposits = stakeDeposits
    # Making date be stored as datetime.
    deposits['Date'] = pd.to_datetime(deposits['Date'])

elif sharesies:
    # UNDER CONSTRUCTION
    pass



# Finding the min date.
fromDate = deposits['Date'].min()
# Finding today's date.
todayDate = date.today()


# Imports USD exchange data.
adjCloseUSD = yf.download('NZDUSD=X', start=fromDate, endDate=todayDate)['Adj Close']


# Forms pandas dataframe containing amount of USD held over time.
# 'Total' should potentially be a total NZD value invested. heldUSD may need renaming!!!!!!!!!!!
cash = pd.DataFrame(index=adjCloseUSD.index, data=0, columns = ['USD cash held', 'NZD invested', 'initial USD bought'])
for i in deposits.index:
    if deposits['Type'][i] == 'Deposit':
        buyDate = deposits['Date'][i]
        boughtUSD = deposits['USD Quantity'][i]
        soldNZD = deposits['NZD Quantity'][i]

        cash.loc[buyDate:,'USD cash held'] += boughtUSD 
        cash.loc[buyDate:,'NZD invested'] += soldNZD

    
    elif deposits['Type'][i] == 'Withdrawal':
        sellDate = deposits['Date'][i]
        soldUSD = deposits['USD Quantity'][i]
        boughtNZD = deposits['NZD Quantity'][i]

        cash.loc[sellDate:, 'USD cash held'] -= soldUSD
        cash.loc[sellDate:, 'NZD invested'] -= boughtNZD
    
    else:
        raise ValueError('Invalid Deposit type')

# Initializing the initial USD bought column.
cash['initial USD bought'] = cash['USD cash held']

# Building string parameter to pass to yf.download containing all tickers.
# Unique stocks:
uniqueStocks = trades['Ticker'].unique()
# Building string:
tickers = uniqueStocks[0]
for stock in range(1, len(uniqueStocks)):
    tickers += ' ' + uniqueStocks[stock]

# Imports data
adjCloseData = yf.download(tickers, start=fromDate, end=todayDate)['Adj Close']


# Forming pandas dataframe containing units of stock for each stock.
unitsData = adjCloseData * 0
for stock in uniqueStocks:
    # Adds stock quantity from buy date to end for each buy order. Treats multiple buy orders in 1 day as 1 order.
    buyOrders = trades[(trades['Type'] == 'BUY') & (trades['Ticker'] == stock)]['Trade Date'].unique()
    for buyOrder in buyOrders:
        currentUnits = np.sum(trades[(trades['Type'] == 'BUY') & (trades['Ticker'] == stock) 
                        & (trades['Trade Date'] == buyOrder)]['Quantity'].to_numpy())
        unitsData.loc[buyOrder:, stock] += currentUnits
    
    # Substracts stock quantity from sell date to end for each sell order. Treats multiple sell orders in 1 day as 1 order.
    sellOrders = trades[(trades['Type'] == 'SELL') & (trades['Ticker'] == stock)]['Trade Date'].unique()
    for sellOrder in sellOrders:
        currentUnits = np.sum(trades[(trades['Type'] == 'SELL') & (trades['Ticker'] == stock) 
                        & (trades['Trade Date'] == sellOrder)]['Quantity'].to_numpy())
        unitsData.loc[sellOrder:, stock] -= currentUnits

investedStockVal = unitsData * adjCloseData
investedStockVal['USD stock value'] = investedStockVal.sum(axis=1)


# Forming the USD cash held column of cash.
for i in trades.index:
    if (trades['Type'][i] == 'BUY'):
        stockUnits = trades['Quantity'][i]
        priceBuy = trades['Price'][i]
        usdUsed = stockUnits * priceBuy
        
        fees = trades['Fees'][i]

        dateBought = trades['Trade Date'][i]

        cash.loc[dateBought:, 'USD cash held'] -= usdUsed + fees
    
    elif (trades['Type'][i] == 'SELL'):
        stockUnits = trades['Quantity'][i]
        priceSell = trades['Price'][i]
        usdUsed = stockUnits * priceSell

        fees = trades['Fees'][i]

        dateSold = trades['Trade Date'][i]

        cash.loc[dateSold:, 'USD cash held'] += usdUsed - fees
    
    else:
        raise ValueError('Invalid Order type')


# Creating infoNZD dataframe containing summarised important information in NZD.
infoNZD = pd.DataFrame(index=investedStockVal.index)
infoNZD['Total value of USD and stocks ($NZD)'] = (investedStockVal['USD stock value'] + cash['USD cash held']) / adjCloseUSD
infoNZD['Total initial NZD invested ($NZD)'] = cash['NZD invested']
infoNZD['Profit/Loss ($NZD)'] = infoNZD['Total value of USD and stocks ($NZD)'] - infoNZD['Total initial NZD invested ($NZD)']
infoNZD['% Profit/Loss'] = infoNZD['Profit/Loss ($NZD)'] / infoNZD['Total initial NZD invested ($NZD)']

# Creating infoUSD dataframe containing summarised important information in USD.
infoUSD = pd.DataFrame(index=investedStockVal.index)
infoUSD['Total value of USD and stocks ($USD)'] = investedStockVal['USD stock value'] + cash['USD cash held']
infoUSD['Total initial USD invested ($USD)'] = cash['initial USD bought']
infoUSD['Profit/Loss ($USD)'] = infoUSD['Total value of USD and stocks ($USD)'] - infoUSD['Total initial USD invested ($USD)']
infoUSD['% Profit/Loss'] = infoUSD['Profit/Loss ($USD)'] / infoUSD['Total initial USD invested ($USD)']


# Forming the NZD plots
fig1, axs1 = plt.subplots(3)
fig1.suptitle('Portolio Tracker ($NZD)')

axs1[0].plot(infoNZD.index, infoNZD['Total value of USD and stocks ($NZD)'], 'b-', label = 'Portfolio Value ($NZD)')
axs1[0].plot(infoNZD.index, infoNZD['Total initial NZD invested ($NZD)'], 'y-', label = 'My Contribution ($NZD)')

axs1[1].plot(infoNZD.index, infoNZD['Profit/Loss ($NZD)'], 'g-', label = 'Profit/Loss ($NZD)')

axs1[2].plot(infoNZD.index, infoNZD['% Profit/Loss'], 'r-', label = '% Profit/Loss')

axs1[0].legend()
axs1[1].legend()
axs1[2].legend()


# Forming the USD plots
fig2, axs2 = plt.subplots(3)
fig2.suptitle('Portolio Tracker ($USD)')

axs2[0].plot(infoUSD.index, infoUSD['Total value of USD and stocks ($USD)'], 'b-', label = 'Portfolio Value ($USD)')
axs2[0].plot(infoUSD.index, infoUSD['Total initial USD invested ($USD)'], 'y-', label = 'My Contribution ($USD)')

axs2[1].plot(infoUSD.index, infoUSD['Profit/Loss ($USD)'], 'g-', label = 'Profit/Loss ($USD)')

axs2[2].plot(infoUSD.index, infoUSD['% Profit/Loss'], 'r-', label = '% Profit/Loss')

axs2[0].legend()
axs2[1].legend()
axs2[2].legend()


plt.show()






pass
