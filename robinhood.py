import os
import requests
import random
import robin_stocks as rs
import yfinance as yf
import pandas as pd
import numpy as np

class Robinhood:
    username = None
    password = None
    auth_token = None
    refresh_token = None
    
    def __init__(self):
        self.device_token = self.GenerateDeviceToken() # generate device token upon initialization
        
    # generates a device token for the user
    # FIND SOURCE FOR THIS 
    def GenerateDeviceToken(self):
        rands = []
        for i in range(0,16):
            r = random.random()
            rand = 4294967296.0 * r
            rands.append((int(rand) >> ((3 & i) << 3)) & 255)

        hexa = []
        for i in range(0,256):
            hexa.append(str(hex(i+256)).lstrip("0x").rstrip("L")[1:])

        id = ""
        for i in range(0,16):
            id += hexa[rands[i]]
            if (i == 3) or (i == 5) or (i == 7) or (i == 9):
                id += "-"

        device_token = id
        return device_token

    '''
    Logs user into their robinhood account
    '''
    def login(self, username, password):
        self.username = username
        self.password = password
        
        # ensure that a device token has been generated
        if self.device_token == "":
                self.GenerateDeviceToken()

        # login via the robinhood api and update global authentication/refresh tokens
        login = rs.login(username, password)
        self.auth_token = login.get('access_token')
        self.refresh_token = login.get('refresh_token')
        return login
    
    # logs user out 
    def logout(self):
        logout = rs.logout()
        self.auth_token = None
        return logout
    
    # prints details of dataframe
    def get_details(self, data):
        print(data.columns)
        print(data.shape)
        print(data.head())
        print(data.info())
        print(data.describe())
        print(data.isnull().sum()) # get cols with null vals
    
    '''
    Takes list of tickers and returns list of latest prices for input stocks
    '''
    def get_prices(self, stocks):
        prices = rs.get_latest_price(stocks)
        for i in range(len(prices)):
            prices[i] = round(float(prices[i]),2)
        return prices
    
    '''
    Takes list of ticker symbols and returns a list of stock names
    '''
    def get_names(self, stocks):
        names = []
        for s in stocks:
            names.append(rs.get_name_by_symbol(s))
        return names
    
    '''
    Takes a ticker and writes historical data to csv file named after the stock
    returns a dataframe of historical data
    '''
    def get_historicals(self, stock, end=None):
        if end:
            df = yf.download(stock, period='2y',end=end)
        else:
            df = yf.download(stock, period='2y')
        # reverse indicies so dates are in decsending order
        #df = df.iloc[::-1]
        df.dropna(inplace=True)
        
        # set type of date,open,close,high,low cols
        df = df.astype({'Open':'float64', 'Close':'float64', 'High':'float64', 'Low':'float64', 'Adj Close':'float64', 'Volume':'int64'})
        df = df.round(2)
        
        # write df to csv file
        df = df.iloc[:-3]
        df.to_csv('historical_data/' + stock + '.csv',index=True)

        return df

    '''
    Updates holdings database table and returns users portfolio as dataframe
    '''
    def get_holdings(self):
        df = pd.DataFrame.from_dict(rs.build_holdings(),'index') # read dict consisting of users portfolio into a df

        # drops useless cols
        df.drop(['average_buy_price', 'equity', 'equity_change', 'type', 'id', 'pe_ratio'], axis=1, inplace=True)

        # Set column names
        df.columns = ['Price', 'Quantity', 'Percent Change', 'Name','Portfolio Percentage']

        # reorder cols
        df = df[['Name', 'Price', 'Percent Change', 'Quantity', 'Portfolio Percentage']]
        
        # convert ticker indicies to column
        df.reset_index(inplace=True)
        df.rename(columns={'index':'Ticker'}, inplace=True)
        
        # set type of date,open,close,high,low cols
        df = df.astype({'Price':'float64', 'Percent Change':'float64', 'Quantity':'float64'})
        df['Quantity'] = df['Quantity'].astype('int64')

        # write df to holdings table in MySQL db
        #df.to_sql('holdings', con=self.connection, if_exists='replace')
        return df
    
    '''
    Updates watchlist database table and returns users watchlist as dataframe
    '''
    def get_watchlist(self):
        holdings = self.get_holdings()
        df = {} # dictionary to create watchlist dataframe
        tickers = []
        
        # return none if watchlist is empty
        if rs.get_watchlist_by_name() is None:
            return None
        
        for d in rs.get_watchlist_by_name():
            url = d.get('instrument')
            ticker = rs.request_get(url).get('symbol')
            
            # if stock is already owned continue
            if ticker in list(holdings['Ticker']):
                continue
            
            tickers.append(ticker)
        
        # create watchlist dataframe
        df = {'Ticker':tickers, 'Name':self.get_names(tickers), 'Price':self.get_prices(tickers)}
        df = pd.DataFrame(df)
        
        # change price col to float
        df = df.astype({'Price':'float64'})
        
        # write df to watchlist table in MySQL db
        #df.to_sql('watchlist', con=self.connection, if_exists='replace')
        return df      
        
if __name__ == '__main__':
    client = Robinhood()
    client.login('', '')
    h = client.get_holdings()
    w = client.get_watchlist()

    
