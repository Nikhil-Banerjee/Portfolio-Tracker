The main script creates an all time investment value and profit/loss graph in NZD taking into account exchange rate fluctuations. 

Currently supports Hatch, Stake and Sharesies. Australian shares on Sharesies are not yet supported.

I have provided my investment data in the repo to use as an example.

If you want to get the portfolio information for your account(s), follow the below instructions and run the `main.py` script file:

# Hatch instructions:
For Hatch, trade data is provided in a file you can download off Hatch however, deposit data must be manually filled.

For trade data go to: Reports -> Order Confirmations -> Export Order Transactions.
For deposit data: Hatch does not provide one. A manual .csv file must be made. Follow format given in the example.

Place 'order-transaction-export-YYYY_MM_DD.csv' file(trade data) and 'Hatch Deposit Data.csv' file(deposit data) inside Hatch folder inside Trade Reports folder (Trade Reports -> Hatch -> "place files").

Delete any other files in the Hatch, Stake and Sharesies folder that is not your data.

# Stake instructions:
For Stake most of the data is provided in a file you can download off Stake. However, the NZD deposited is not provided. You can manually provide the data for this but this is optional. Instead this script finds the NZD deposited by looking at NZD closing prices for the day it was deposited (obviously not accurate but still good enough).

Go to Transaction report and download the Excel(detailed report) file for the date range you wish to graph.

Place file inside Stake folder inside Trade Reports folder (Trade Reports -> Stake -> "place file").

Optional: You can find the exact NZD deposited for each transaction by going to the deposit tab (dollar bill icon top right). Once there manually add onto the Deposits & Withdrawals sheet by putting your NZD deposits on a new column (you will create) called NZD Quantity. See given excel file for example. 

Delete any other files in the Hatch, Stake and Sharesies folder that is not your data.

# Sharesies instructions:
For Sharesies all data is provided in a file you can download off Sharesies.

Go to: Settings -> Reports -> Transaction Report(csv) for the desired date range.

Place file inside Sharesies folder inside Trade Reports folder (Trade Reports -> Sharesies -> "place file").

Delete any other files in the Hatch, Stake and Sharesies folder that is not your data.


**Above info accurate as of 6 July 2022.**
-Nikhil Banerjee
