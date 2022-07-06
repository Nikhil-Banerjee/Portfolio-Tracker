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
# NZ and US dates are taken at face value.
# NZD cash held in sharesies is not counted as portfolio value but Hatch and Stake cash is counted.
# Buy orders before stock splits.

def hatchRead(tradeFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + 'order-transaction*.csv')[-1],
        depositFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + 'Hatch Deposit Data.csv')[0]):
    """
    - This function reads in all the data from hatch in 2 concise dataframes.
    - Reads in trade data from provided hatch file. Works for format as of 5/7/21.
    - A deposit/withdrawal .csv file needs to be made manually to be read in.

    Parameters
    ----------
    tradeFilePath   : string
                        A string containing the file path for the file containing hatch trade data.
                        This is the provided hatch file.
    depositFilePath : string
                        A string containing the file path for the file containing hatch deposit/withdrawal data.
                        This needs to be manually made.
    
    Returns
    -------
    trades   : pandas dataframe
                Contains all relevant hatch trade data.

    deposits : pandas dataframe
                Contains all relevant hatch deposit data.
    
    Notes 
    -----
    - The trade fees for each trade is assumed to be 3 USD (true as of 17/7/21).
    - All stocks are assumed to be US stocks.
    """

    trades = pd.read_csv(tradeFilePath)
    # Simplifying hatchTrades dataframe.
    trades = trades.assign(Fees=3) # Forms a new column containing the flat $3 fee for each trade.
    trades = trades.assign(Currency='USD')
    trades = trades.drop(['Comments'], axis=1) # Removes the comments column.
    trades = trades.rename({'Instrument Code' : 'Ticker', 'Transaction Type' : 'Type'}, axis=1)

    # Reads in deposit data from Hatch
    # The .csv file to be read is manually made. Hatch does not provide any deposit information as of 5/7/21.
    deposits = pd.read_csv(depositFilePath)

    return trades, deposits


def stakeRead(filePath = glob('trade reports' + os.sep + 'stake' + os.sep + '*.xlsx')[0]):
    """
    - This function reads in all the data from Stake in 2 concise dataframes.
    - Reads in trade and some deposit data using provided stake excel file.
    - NZD values of deposits and withdrawals need to be manually filled in, inside the same file.

    Parameters
    ----------
    filePath   : string
                        A string containing the file path for the file containing Stake data.
                        This is the provided Stake excel file.
    
    Returns
    -------
    trades   : pandas dataframe
                Contains all relevant Stake trade data.

    deposits : pandas dataframe
                Contains all relevant Stake deposit data.
    
    Notes 
    -----
    - All stocks are assumed to be US stocks.
    - Works as of 5/7/21.
    """
    trades = pd.read_excel(filePath, sheet_name='Trades')
    # Simplifying stakeTrades dataframe.
    # Renaming data and keeping only relevant data to match overall convention:
    trades = trades.rename({'SETTLEMENT DATE (US)' : 'Trade Date', 'SIDE' : 'Type', 
                                    'UNITS' : 'Quantity', 'EFFECTIVE PRICE (USD)' : 'Price', 
                                    'BROKERAGE FEE (USD)' : 'Fees', 'SYMBOL' : 'Ticker'}, axis=1) 
    trades = trades[['Trade Date', 'Type', 'Quantity', 'Price', 'Fees', 'Ticker']]

    # Reassigning B/S values in Type to BUY/SELL to match hatch convention:
    trades['Type'] = np.where(trades['Type'] == 'B', 'BUY', 'SELL')
    # Forming column containing currency of stocks.
    trades = trades.assign(Currency='USD')

    # Reads in deposit data from Stake
    # The provided Stake report does not contain the NZD amounts as of 5/7/21. This needs to be added manually.
    deposits = pd.read_excel(filePath, sheet_name='Deposits & Withdrawals')
    # Simplifying stakeDeposits dataframe:
    # Renaming data.
    deposits = deposits.rename({'DATE (US)' : 'Date', 'FUNDING TYPE' : 'Type', 
                                        'RECEIVE AMOUNT (USD)' : 'USD Quantity'}, axis=1)
    
    # If NZD quantity purchase not given.
    if not ('NZD Quantity' in deposits.columns):

        nzdForUSD = yf.download('USDNZD=X', start=deposits.iloc[0]['Date'])['Adj Close']
        deposits = deposits.merge(nzdForUSD, 'left', 'Date')
        deposits['NZD Quantity'] = deposits['Adj Close'] * deposits['USD Quantity']

    deposits = deposits[['Date', 'Type', 'USD Quantity', 'NZD Quantity']]

    return trades, deposits

def sharesiesRead(filePath = glob('trade reports' + os.sep + 'sharesies' + os.sep + 'transaction-report.csv')[0]):
    """
    - This function reads in all the data from Sharesies in 2 concise dataframes.
    - Reads in trade and US deposit data using provided sharesies file.
    - All information is read through provided sharesies file.
    - Does not take into account NZD cash held in account.

    Parameters
    ----------
    filePath   : string
                        A string containing the file path for the file containing Sharesies data.
                        This is the provided Sharesies file.
    
    Returns
    -------
    trades   : pandas dataframe
                Contains all relevant Sharesies trade data.

    deposits : pandas dataframe
                Contains all relevant Sharesies deposit data.
    
    Notes 
    -----
    - Stock is assumed to be US stock if currency is USD.
    - Stock is assumed to be NZ stock if currency is NZD.
    - USD is assumed to be bought when a US stock is bought and USD is sold when a US stock is sold.
    - Works as of 5/7/21, does not work for Australian stocks.
    """

    trades = pd.read_csv(filePath)
    # Simplifying sharesiesTrades dataframe:
    # Renaming data to match convention:
    trades = trades.rename({'Instrument code' : 'Ticker', 'Transaction type' : 'Type', \
                            'Transaction fee' : 'Fees', 'Trade date' : 'Trade Date'}, axis=1)
    # Adding .NZ suffix to ticker for every NZ stock:
    trades['Ticker'] = np.where(trades['Currency'] == 'NZD', \
                                        trades['Ticker'] + '.NZ', \
                                        trades['Ticker'])

    # Sharesies deposit data(only interested in USD deposits only) is contained in the trade report.
    deposits = pd.DataFrame(columns=['Date', 'Type', 'USD Quantity', 'NZD Quantity'])

    usStockIndices = trades.index[trades['Currency'] == 'USD']

    # Extracting deposit data from sharesies trade report csv file (sharesies does instant transfer to/from USD for each trade):
    deposits['Date'] = trades.loc[usStockIndices, 'Trade Date']
    # Classes a buy trade as a deposit and withdrawal OTHERWISE.
    deposits['Type'] = np.where(trades.loc[usStockIndices, 'Type'] == 'BUY', 'Deposit', 'Withdrawal')
    # Storing the USD and NZD amounts of each US trade.
    deposits['USD Quantity'] = trades.loc[usStockIndices, 'Amount']
    deposits['NZD Quantity'] = np.where(trades.loc[usStockIndices, 'Type'] == 'BUY', \
                    trades.loc[usStockIndices, 'Amount'] / trades.loc[usStockIndices, 'Exchange rate'], \
                    trades.loc[usStockIndices, 'Amount'] * trades.loc[usStockIndices, 'Exchange rate'])
   
    # Keeping only relevant data.
    trades = trades[['Trade Date', 'Type', 'Quantity', 'Price', 'Fees', 'Ticker', 'Currency']]

    return trades, deposits


def initialInvest(trades, startDate, endDate):
    """
    This function forms a pandas series that contains the initial investment value over time.

    Parameters
    ----------
    trades    : pandas dataframe
                dataframe containing all trade information.

    startDate : datetime value
                date at which the pandas series needs to start.

    endDate   : datetime value 
                date at which the pandas series needs to end.
    
    Returns
    -------
    initialInvestment : pandas series
                        dataframe containing initial investment value over time. Index is a datetime range.

    """
    initialInvestment = pd.Series(index=pd.date_range(startDate, endDate), name='$NZD',data=0)
    trades.loc[:, "NZD traded"] = trades.Price * trades.Quantity


    for trade in trades.index:
        if trades.loc[trade, 'Type'] == 'BUY':
            buyDate = trades.loc[trade, 'Trade Date']
            bought = trades.loc[trade, 'NZD traded']

            initialInvestment.loc[buyDate:] += bought
    
        elif trades.loc[trade, 'Type'] == 'SELL':
            sellDate = trades.loc[trade, 'Trade Date']
            sold = trades.loc[trade, 'NZD traded']

            initialInvestment.loc[sellDate:] -= sold
    
        else:
            raise ValueError('Invalid trade type')
    
    return initialInvestment

def USDOverTime(deposits, startDate, endDate, tradesUS):
    """
    This function forms a dataframe containining USD cash held over time, NZD invested in USD over time, Initial USD bought over time.

    Parameters
    ----------
    deposits  : pandas dataframe
                dataframe containing all information about deposits/withdrawals.

    startDate : datetime value
                date at which the pandas dataframe index starts.

    endDate   : datetime value
                date at which the pandas dataframe index ends.
    
    Returns
    -------
    cash : pandas dataframe
            dataframe containing all the required information.
    """
    
    cash = pd.DataFrame(index=pd.date_range(startDate, endDate), data=0, columns = ['USD cash held', 'NZD invested in USD', 'initial USD bought'])

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

    return cash

def stockStringBuilder(tickerSeries):
    """
    Builds string to pass to yf.download containing all individual tickers.
    
    Parameters
    ----------
    tickerSeries : pandas series
                    Series containing tickers to pass. Duplicate entries are allowed.
    
    Returns
    -------
    tickerStr : string
                Required parameter to find multiple stock data for yf.download().
    """

    # Building string parameters to pass to yf.download containing all tickers (NZ and US seperate).
    # Unique stocks for US:
    uniqueStocks = tickerSeries.unique()
    # Building string:
    tickerStr = uniqueStocks[0]
    for stock in range(1, len(uniqueStocks)):
        tickerStr += ' ' + uniqueStocks[stock]

    return tickerStr

def unitsOverTime(trades, df):
    """
    Forms a dataframe containing quantity over time for each stock in trades dataframe.

    Parameters
    ----------
    trade : pandas dataframe
            dataframe containing all trade information.
    
    df    : pandas dataframe
            dataframe used as format for return dataframe. 
            Slow method, but later fix will remove this need to pass another big dataframe.
    
    Returns
    -------
    units : pandas dataframe
            dataframe containing units over time for all stocks
    """
    

    units = df * 0
    for stock in trades['Ticker'].unique():
        # Adds stock quantity from buy date to end for each buy order. Treats multiple buy orders in 1 day as 1 order.
        buyOrders = trades[(trades['Type'] == 'BUY') & (trades['Ticker'] == stock)]['Trade Date'].unique()
        for buyOrder in buyOrders:
            currentUnits = np.sum(trades[(trades['Type'] == 'BUY') & (trades['Ticker'] == stock) 
                            & (trades['Trade Date'] == buyOrder)]['Quantity'].to_numpy())
            units.loc[buyOrder:, stock] += currentUnits
        
        # Substracts stock quantity from sell date to end for each sell order. Treats multiple sell orders in 1 day as 1 order.
        sellOrders = trades[(trades['Type'] == 'SELL') & (trades['Ticker'] == stock)]['Trade Date'].unique()
        for sellOrder in sellOrders:
            currentUnits = np.sum(trades[(trades['Type'] == 'SELL') & (trades['Ticker'] == stock) 
                            & (trades['Trade Date'] == sellOrder)]['Quantity'].to_numpy())
            units.loc[sellOrder:, stock] -= currentUnits
    
    return units

if __name__ == '__main__':

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