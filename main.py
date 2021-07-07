import pandas as pd
import numpy as np
import os
from glob import glob
from datetime import date
from pandas._libs.tslibs import NaT
from pandas.core.indexes.datetimes import date_range
import yfinance as yf
from matplotlib import pyplot as plt

# Potential problems: 
# does not take into account non-trade fees (Stake Black).
# NZ and US dates are all jumbled up.


# Controls which data should be read
hatch = True
stake = True
sharesies = True

tradesArray = []
depositsArray = []

# Reads in trades from hatch as pandas dataframe. File format works as of 5/7/21.
if hatch:
    hatchTradeFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + 'order-transaction*.csv')
    hatchTrades = pd.read_csv(hatchTradeFilePath[0])
    # Simplifying hatchTrades dataframe.
    hatchTrades = hatchTrades.assign(Fees=3) # Forms a new column containing the flat $3 fee for each trade.
    hatchTrades = hatchTrades.assign(Currency='USD')
    hatchTrades = hatchTrades.drop(['Comments'], axis=1) # Removes the comments column.
    hatchTrades = hatchTrades.rename({'Instrument Code' : 'Ticker', 'Transaction Type' : 'Type'}, axis=1)

    tradesArray.append(hatchTrades)

    # Reads in deposit data from Hatch
    # The .csv file to be read is manually made. Hatch does not provide any deposit information as of 5/7/21.
    hatchDepositFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + 'Hatch Deposit Data.csv')
    hatchDeposits = pd.read_csv(hatchDepositFilePath[0])    

    depositsArray.append(hatchDeposits)



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
    # Forming column containing currency of stocks.
    stakeTrades = stakeTrades.assign(Currency='USD')

    tradesArray.append(stakeTrades)

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
    
    depositsArray.append(stakeDeposits)



# Reads in trades from Sharesies 
# No manual input of data required at all as of 7/7/21.
if sharesies:
    # Reads in trades from Sharesies.
    sharesiesFilePath = glob('trade reports' + os.sep + 'sharesies' + os.sep + 'transaction-report.csv')
    sharesiesTrades = pd.read_csv(sharesiesFilePath[0])
    # Simplifying sharesiesTrades dataframe:
    # Renaming data to match convention:
    sharesiesTrades = sharesiesTrades.rename({'Instrument code' : 'Ticker', 'Transaction type' : 'Type', \
                                            'Transaction fee' : 'Fees', 'Trade date' : 'Trade Date'}, axis=1)
    # Adding .NZ suffix for every NZ stock:
    sharesiesTrades['Ticker'] = np.where(sharesiesTrades['Currency'] == 'NZD', \
                                        sharesiesTrades['Ticker'] + '.NZ', \
                                        sharesiesTrades['Ticker'])

    # Sharesies deposit data(only interested in USD deposits only) is contained in the trade report.
    sharesiesDeposits = pd.DataFrame(columns=['Date', 'Type', 'USD Quantity', 'NZD Quantity'])
    # indices of US stocks
    usStockIndices = sharesiesTrades.index[sharesiesTrades['Currency'] == 'USD']

    # Extracting deposit data from sharesies trade report csv file (sharesies does instant transfer to/from USD for each trade):
    # Saving dates of each US trade.
    sharesiesDeposits['Date'] = sharesiesTrades.loc[usStockIndices, 'Trade Date']
    # Classes a buy trade as a deposit and withdrawal OTHERWISE.
    sharesiesDeposits['Type'] = np.where(sharesiesTrades.loc[usStockIndices, 'Type'] == 'BUY', 'Deposit', 'Withdrawal')
    # Storing the USD and NZD amounts of each US trade.
    sharesiesDeposits['USD Quantity'] = sharesiesTrades.loc[usStockIndices, 'Amount']
    sharesiesDeposits['NZD Quantity'] = np.where(sharesiesTrades.loc[usStockIndices, 'Type'] == 'BUY', \
                    sharesiesTrades.loc[usStockIndices, 'Amount'] / sharesiesTrades.loc[usStockIndices, 'Exchange rate'], \
                    sharesiesTrades.loc[usStockIndices, 'Amount'] * sharesiesTrades.loc[usStockIndices, 'Exchange rate'])
   
    # Removing useless data from sharesies trade dataframe.
    sharesiesTrades = sharesiesTrades.drop(['Order ID', 'Market code', 'Amount', 'Transaction method', 'Exchange rate'], \
                     axis=1)
    
    tradesArray.append(sharesiesTrades)
    depositsArray.append(sharesiesDeposits)
    


trades = pd.concat(tradesArray, ignore_index=True)
# Making Trade date be stored as datetime.
trades['Trade Date'] = pd.to_datetime(trades['Trade Date'])

# Combining deposits dataframes
deposits = pd.concat(depositsArray, ignore_index=True)
# Making date be stored as datetime.
deposits['Date'] = pd.to_datetime(deposits['Date'])


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


# Forming pandas dataframe containing amount of NZD invested over time.
NZDinvestedNZstocks = pd.Series(index=pd.date_range(fromDate, todayDate), name='$NZD',data=0)
tradesNZ.loc[:, "NZD traded"] = tradesNZ.Price * tradesNZ.Quantity


for trade in tradesNZ.index:
    if tradesNZ.loc[trade, 'Type'] == 'BUY':
        buyDate = tradesNZ.loc[trade, 'Trade Date']
        bought = tradesNZ.loc[trade, 'NZD traded']

        NZDinvestedNZstocks.loc[buyDate:] += bought
    
    elif tradesNZ.loc[trade, 'Type'] == 'SELL':
        sellDate = tradesNZ.loc[trade, 'Trade Date']
        sold = tradesNZ.loc[trade, 'NZD traded']

        NZDinvestedNZstocks.loc[sellDate:] -= sold
    
    else:
        raise ValueError('Invalid trade type')


# Forms pandas dataframe containing amount of USD held over time.
# 'Total' should potentially be a total NZD value invested. heldUSD may need renaming!!!!!!!!!!!
cash = pd.DataFrame(index=adjCloseUSD.index, data=0, columns = ['USD cash held', 'NZD invested in USD', 'initial USD bought'])
for i in deposits.index:
    if deposits['Type'][i] == 'Deposit':
        buyDate = deposits['Date'][i]
        boughtUSD = deposits['USD Quantity'][i]
        soldNZD = deposits['NZD Quantity'][i]

        cash.loc[buyDate:,'USD cash held'] += boughtUSD 
        cash.loc[buyDate:,'NZD invested in USD'] += soldNZD

    elif deposits['Type'][i] == 'Withdrawal':
        sellDate = deposits['Date'][i]
        soldUSD = deposits['USD Quantity'][i]
        boughtNZD = deposits['NZD Quantity'][i]

        cash.loc[sellDate:, 'USD cash held'] -= soldUSD
        cash.loc[sellDate:, 'NZD invested in USD'] -= boughtNZD
    
    else:
        raise ValueError('Invalid Deposit type')

# Initializing the initial USD bought column.
cash['initial USD bought'] = cash['USD cash held']

# Building string parameters to pass to yf.download containing all tickers (NZ and US seperate).
# Unique stocks for US:
uniqueStocksUS = tradesUS['Ticker'].unique()
# Building string:
tickersUS = uniqueStocksUS[0]
for stock in range(1, len(uniqueStocksUS)):
    tickersUS += ' ' + uniqueStocksUS[stock]

# Unique stocks for NZ:
uniqueStocksNZ = tradesNZ['Ticker'].unique()
# Building string:
tickersNZ = uniqueStocksNZ[0]
for stock in range(1, len(uniqueStocksNZ)):
    tickersNZ += ' ' + uniqueStocksNZ[stock]


# Imports data for US stocks
adjCloseDataUS = yf.download(tickersUS, start=fromDate, end=todayDate)['Adj Close']
# Imports data for NZ stocks
adjCloseDataNZ = yf.download(tickersNZ, start=fromDate, end=todayDate)['Adj Close']


# Forming pandas dataframe containing units of stock for each US stock.
unitsDataUS = adjCloseDataUS * 0
for stock in uniqueStocksUS:
    # Adds stock quantity from buy date to end for each buy order. Treats multiple buy orders in 1 day as 1 order.
    buyOrders = tradesUS[(tradesUS['Type'] == 'BUY') & (tradesUS['Ticker'] == stock)]['Trade Date'].unique()
    for buyOrder in buyOrders:
        currentUnits = np.sum(tradesUS[(tradesUS['Type'] == 'BUY') & (tradesUS['Ticker'] == stock) 
                        & (tradesUS['Trade Date'] == buyOrder)]['Quantity'].to_numpy())
        unitsDataUS.loc[buyOrder:, stock] += currentUnits
    
    # Substracts stock quantity from sell date to end for each sell order. Treats multiple sell orders in 1 day as 1 order.
    sellOrders = tradesUS[(tradesUS['Type'] == 'SELL') & (tradesUS['Ticker'] == stock)]['Trade Date'].unique()
    for sellOrder in sellOrders:
        currentUnits = np.sum(tradesUS[(tradesUS['Type'] == 'SELL') & (tradesUS['Ticker'] == stock) 
                        & (tradesUS['Trade Date'] == sellOrder)]['Quantity'].to_numpy())
        unitsDataUS.loc[sellOrder:, stock] -= currentUnits

# Forming pandas dataframe containing units of stock for each NZ stock.
unitsDataNZ = adjCloseDataNZ * 0
for stock in uniqueStocksNZ:
    # Adds stock quantity from buy date to end for each buy order. Treats multiple buy orders in 1 day as 1 order.
    buyOrders = tradesNZ[(tradesNZ['Type'] == 'BUY') & (tradesNZ['Ticker'] == stock)]['Trade Date'].unique()
    for buyOrder in buyOrders:
        currentUnits = np.sum(tradesNZ[(tradesNZ['Type'] == 'BUY') & (tradesNZ['Ticker'] == stock) 
                        & (tradesNZ['Trade Date'] == buyOrder)]['Quantity'].to_numpy())
        unitsDataNZ.loc[buyOrder:, stock] += currentUnits

    # Substracts stock quantity from sell date to end for each sell order. Treats multiple sell orders in 1 day as 1 order.
    sellOrders = tradesNZ[(tradesNZ['Type'] == 'SELL') & (tradesNZ['Ticker'] == stock)]['Trade Date'].unique()
    for sellOrder in sellOrders:
        currentUnits = np.sum(tradesNZ[(tradesNZ['Type'] == 'SELL') & (tradesNZ['Ticker'] == stock) 
                        & (tradesNZ['Trade Date'] == sellOrder)]['Quantity'].to_numpy())
        unitsDataNZ.loc[sellOrder:, stock] -= currentUnits


# Calculating values of investments in respective currencies
# For US stocks.
investedStockValUS = unitsDataUS * adjCloseDataUS
investedStockValUS['USD stock value'] = investedStockValUS.sum(axis=1)
# For NZ stocks.
investedStockValNZ = unitsDataNZ * adjCloseDataNZ
investedStockValNZ['NZD stock value'] = investedStockValNZ.sum(axis=1)


# Forming the USD cash held column of cash.
for i in tradesUS.index:
    if (tradesUS['Type'][i] == 'BUY'):
        stockUnits = tradesUS['Quantity'][i]
        priceBuy = tradesUS['Price'][i]
        usdUsed = stockUnits * priceBuy
        
        fees = tradesUS['Fees'][i]

        dateBought = tradesUS['Trade Date'][i]

        cash.loc[dateBought:, 'USD cash held'] -= usdUsed + fees
    
    elif (tradesUS['Type'][i] == 'SELL'):
        stockUnits = tradesUS['Quantity'][i]
        priceSell = tradesUS['Price'][i]
        usdUsed = stockUnits * priceSell

        fees = tradesUS['Fees'][i]

        dateSold = tradesUS['Trade Date'][i]

        cash.loc[dateSold:, 'USD cash held'] += usdUsed - fees
    
    else:
        raise ValueError('Invalid Order type')


# forward filling investedStockVal and forex data with missing values.
investedStockValUS = investedStockValUS.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
investedStockValNZ = investedStockValNZ.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
adjCloseNZD = adjCloseNZD.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
adjCloseUSD = adjCloseUSD.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')
cash = cash.reindex(pd.date_range(fromDate, todayDate)).fillna(method='ffill')


# Creating infoUSD dataframe containing summarised important information in USD about US stocks.
infoUSDstockUS = pd.DataFrame(index=investedStockValUS.index)
infoUSDstockUS['Total value of investment'] = investedStockValUS['USD stock value'].add(cash['USD cash held'])
infoUSDstockUS['Total initial investment'] = cash['initial USD bought']
infoUSDstockUS['Profit/Loss'] = infoUSDstockUS['Total value of investment'].sub(infoUSDstockUS['Total initial investment'])
# infoUSDstockUS['% Profit/Loss'] = infoUSDstockUS['Profit/Loss ($USD)'].div(infoUSDstockUS['Total initial USD invested ($USD)'])

# Creating infoNZD dataframe containing summarised important information in NZD about US stocks.
infoNZDStockUS = pd.DataFrame(index=investedStockValUS.index)
infoNZDStockUS['Total value of investment'] = infoUSDstockUS['Total value of investment'] * adjCloseNZD
infoNZDStockUS['Total initial investment'] = cash['NZD invested in USD']
infoNZDStockUS['Profit/Loss'] = infoNZDStockUS['Total value of investment'].sub(infoNZDStockUS['Total initial investment'])
# infoNZDStockUS['% Profit/Loss'] = infoNZDStockUS['Profit/Loss ($NZD)'].div(infoNZDStockUS['Total initial NZD invested ($NZD)'])

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
infoOverall_NZD['% Profit/Loss'] = infoOverall_NZD['Profit/Loss'] / infoOverall_NZD['Total initial investment']


# # Forming the NZD plots
# fig1, axs1 = plt.subplots(3)
# fig1.suptitle('Portolio Tracker ($NZD)')

# axs1[0].plot(infoNZDStockUS.index, infoNZDStockUS['Total value of USD and stocks ($NZD)'], 'b-', label = 'Portfolio Value ($NZD)')
# axs1[0].plot(infoNZDStockUS.index, infoNZDStockUS['Total initial NZD invested ($NZD)'], 'y-', label = 'My Contribution ($NZD)')

# axs1[1].plot(infoNZDStockUS.index, infoNZDStockUS['Profit/Loss ($NZD)'], 'g-', label = 'Profit/Loss ($NZD)')

# axs1[2].plot(infoNZDStockUS.index, infoNZDStockUS['% Profit/Loss'], 'r-', label = '% Profit/Loss')

# axs1[0].legend()
# axs1[1].legend()
# axs1[2].legend()


# # Forming the USD plots
# fig2, axs2 = plt.subplots(3)
# fig2.suptitle('Portolio Tracker ($USD)')

# axs2[0].plot(infoUSDstockUS.index, infoUSDstockUS['Total value of USD and stocks ($USD)'], 'b-', label = 'Portfolio Value ($USD)')
# axs2[0].plot(infoUSDstockUS.index, infoUSDstockUS['Total initial USD invested ($USD)'], 'y-', label = 'My Contribution ($USD)')

# axs2[1].plot(infoUSDstockUS.index, infoUSDstockUS['Profit/Loss ($USD)'], 'g-', label = 'Profit/Loss ($USD)')

# axs2[2].plot(infoUSDstockUS.index, infoUSDstockUS['% Profit/Loss'], 'r-', label = '% Profit/Loss')

# axs2[0].legend()
# axs2[1].legend()
# axs2[2].legend()

fig, ax = plt.subplots(3)
fig.suptitle('Portfolio Tracker ($NZD)')

ax[0].plot(infoOverall_NZD.index, infoOverall_NZD['Total value of investment'], 'g-', label='Portfolio value ($NZD)')
ax[0].plot(infoOverall_NZD.index, infoOverall_NZD['Total initial investment'], 'b-', label='My contribution ($NZD)')

ax[1].plot(infoOverall_NZD.index, infoOverall_NZD['Profit/Loss'], 'r-', label='Profit/Loss ($NZD)')

ax[2].plot(infoOverall_NZD.index, infoOverall_NZD['% Profit/Loss'], 'k-', label='% Profit/Loss')


# Displaying summarised current information:
print(f"The current porfolio value is ${infoOverall_NZD.loc[str(todayDate), 'Total value of investment']:.2f}.")
print(f"The initial investment value is ${infoOverall_NZD.loc[str(todayDate), 'Total initial investment']:.2f}.")
print(f"The current Profit/Loss is ${infoOverall_NZD.loc[str(todayDate), 'Profit/Loss']:.2f}.")
print(f"The current % Profit/Loss is {infoOverall_NZD.loc[str(todayDate), '% Profit/Loss']*100:.2f}%.")

plt.show()






pass
