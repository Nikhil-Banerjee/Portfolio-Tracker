import pandas as pd
import numpy as np
import os
from glob import glob


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


# Combining dataframes
trades = pd.concat([hatchTrades, stakeTrades], ignore_index=True)


pass
