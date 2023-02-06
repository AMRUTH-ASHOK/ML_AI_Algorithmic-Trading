import pandas as pd
import numpy as np
import fxcmpy
import time
from datetime import datetime

col = ["tradeId", "amountK", "currency", "grossPL", "isBuy"]

class ConTrader():
    
    def __init__(self, instrument, bar_length, SMA_S,SMA_L, units):
        self.instrument = instrument
        self.bar_length = pd.to_timedelta(bar_length) 
        self.tick_data = None
        self.raw_data = None
        self.data = None 
        self.ticks = 0
        self.last_bar = None  
        self.units = units
        self.position = 0
        self.flag = 0 # to skip first execution of execute_trades()
        
        
        #*****************add strategy-specific attributes here******************
        self.SMA_S = SMA_S
        self.SMA_L = SMA_L
        #************************************************************************        
    
    def get_most_recent(self, period = "m1", number = 10000):
        while True:  
            time.sleep(5)
            df = api.get_candles(self.instrument, number = number, period = period, columns = ["bidclose", "askclose"])
            df[self.instrument] = (df.bidclose + df.askclose) / 2
            df = df[self.instrument].to_frame()
            df = df.resample(self.bar_length, label = "right").last().dropna().iloc[:-1]
            self.raw_data = df.copy()
            self.last_bar = self.raw_data.index[-1]
            if pd.to_datetime(datetime.utcnow()) - self.last_bar < self.bar_length:
                break
    
    def get_tick_data(self, data, dataframe):
        
        self.ticks += 1
        print(self.ticks, end = " ", flush = True)
        
        recent_tick = pd.to_datetime(data["Updated"], unit = "ms")
        
        if recent_tick - self.last_bar > self.bar_length:
            self.tick_data = dataframe.loc[self.last_bar:, ["Bid", "Ask"]]
            self.tick_data[self.instrument] = (self.tick_data.Ask + self.tick_data.Bid)/2
            self.tick_data = self.tick_data[self.instrument].to_frame()
            self.resample_and_join()
            self.define_strategy() 
            self.execute_trades()
            
    def resample_and_join(self):
        self.raw_data = self.raw_data.append(self.tick_data.resample(self.bar_length, 
                                                             label="right").last().ffill().iloc[:-1])
        self.last_bar = self.raw_data.index[-1]  
        #print the whole dataframe
        print(self.data)

    # simple moving average strategy
    def define_strategy(self): # "strategy-specific"
        df = self.raw_data.copy()
        
         #******************** define strategy here ************************
        df["SMA_S"] = df[self.instrument].rolling(self.SMA_S).mean()
        df["SMA_L"] = df[self.instrument].rolling(self.SMA_L).mean()
        df["position"] = np.where(df["SMA_S"] > df["SMA_L"], 1, -1)
        #***********************************************************************
        
        self.data = df.copy()

    # # Exponential moving average strategy
    # def define_strategy(self): # "strategy-specific"
    #     df = self.raw_data.copy()

    #     #******************** define strategy here ************************
    #     df["EMA_S"] = df[self.instrument].ewm(span = self.EMA_S).mean()
    #     df["EMA_L"] = df[self.instrument].ewm(span = self.EMA_L).mean()
    #     df["position"] = np.where(df["EMA_S"] > df["EMA_L"], 1, -1)
    #     #***********************************************************************

    #     self.data = df.copy()


    # skip execution the first time    
    def execute_trades(self):
        if self.flag == 0:
            print("skipping first execution")
            self.flag = 1
        else:
            if self.data["position"].iloc[-1] == 1:
                if self.position == 0:
                    order = api.create_market_buy_order(self.instrument, self.units)
                    self.report_trade(order, "GOING LONG")  
                elif self.position == -1:
                    order = api.create_market_buy_order(self.instrument, self.units * 2)
                    self.report_trade(order, "GOING LONG")  
                self.position = 1
            elif self.data["position"].iloc[-1] == -1: 
                if self.position == 0:
                    order = api.create_market_sell_order(self.instrument, self.units)
                    self.report_trade(order, "GOING SHORT")  
                elif self.position == 1:
                    order = api.create_market_sell_order(self.instrument, self.units * 2)
                    self.report_trade(order, "GOING SHORT")  
                self.position = -1
            elif self.data["position"].iloc[-1] == 0: 
                if self.position == -1:
                    order = api.create_market_buy_order(self.instrument, self.units)
                    self.report_trade(order, "GOING NEUTRAL")  
                elif self.position == 1:
                    order = api.create_market_sell_order(self.instrument, self.units)
                    self.report_trade(order, "GOING NEUTRAL")  
                self.position = 0


    def report_trade(self, order, going):  
        time = order.get_time()
        units = api.get_open_positions().amountK.iloc[-1]
        price = api.get_open_positions().open.iloc[-1]
        unreal_pl = api.get_open_positions().grossPL.sum()
        print("\n" + 100* "-")
        print("{} | {}".format(time, going))
        print("{} | units = {} | price = {} | Unreal. P&L = {}".format(time, units, price, unreal_pl))
        # print current SMA values
        print("{} | SMA_S = {} | SMA_L = {}".format(time, self.data.SMA_S.iloc[-1], self.data.SMA_L.iloc[-1]))
        print(100 * "-" + "\n")
        # write to csv
        with open("trades.csv", "a") as f:
            f.write("{},{},{},{},{}\n".format(self.instrument,time, going, units, price, unreal_pl))
        
if __name__ == "__main__":  
    api = fxcmpy.fxcmpy(config_file = "/Users/amruthashok/Desktop/AI-Trader/Trader/FXCM.cfg")
    trader = ConTrader("EUR/USD", bar_length = "5min", SMA_S=10,SMA_L=30, units = 1)
    trader.get_most_recent()
    api.subscribe_market_data(trader.instrument, (trader.get_tick_data, ))
