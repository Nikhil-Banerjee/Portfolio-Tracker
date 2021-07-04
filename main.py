import pandas as pd
import os
from glob import glob


# Reads in trades from hatch
hatchFilePath = glob('trade reports' + os.sep + 'hatch' + os.sep + '*.csv')
hatchTrades = pd.read_csv(hatchFilePath[0])

# Reads in trades from Stake
stakeFilePath = glob('trade reports' + os.sep + 'stake' + os.sep + '*.xlsx')
stakeTrades = pd.read_excel(stakeFilePath[0], sheet_name='Trades')

# Reads in trades from Sharesies
# UNDER CONSTRUCTION

