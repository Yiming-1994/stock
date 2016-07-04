#!/usr/local/bin/python
#coding=utf-8

#实时均线策略

import pandas as pd
import numpy as np
from data_process.data_calcute import calcute_ma

from init import *


class MAStrategy:
    
    # df: DataFrame    
    def __init__(self, stockData='', df=''):
        
        self.AVR_SHORT = AVR_SHORT
        self.AVR_LONG = AVR_LONG

        #方式二
        # 将数据按照交易日期从远到近排序
        df.sort(columns='date', inplace=True)

        df = calcute_ma(df, AVR_SHORT, AVR_LONG)

        # print df.tail()
        self.close_price = df['close'].get_values()

        self.close_price = np.append(self.close_price, float(stockData.current))

        #计算当前的ma
        lastest_ma_short = sum(self.close_price[-self.AVR_SHORT:])/self.AVR_SHORT;
        lastest_ma_long = sum(self.close_price[-self.AVR_LONG:])/self.AVR_LONG;

        self.ma_short = np.append(df['ma_%d' % self.AVR_SHORT].get_values(), lastest_ma_short)
        self.ma_long = np.append(df['ma_%d' % self.AVR_LONG].get_values(), lastest_ma_long)

        #计算当前的ema
        self.ema_short = df["ema_%d" % self.AVR_SHORT].get_values()
        self.ema_long = df["ema_%d" % self.AVR_LONG].get_values()
        lastest_ema_short = self.ema_short[-2] * (self.AVR_SHORT-1)/(self.AVR_SHORT+1) + stockData.current * 2 /(self.AVR_SHORT+1)
        lastest_ema_long = self.ema_long[-2] * (self.AVR_LONG-1)/(self.AVR_LONG+1) + stockData.current * 2 /(self.AVR_LONG+1)

        self.ema_short = np.append(self.ema_short, lastest_ema_short)
        self.ema_long = np.append(self.ema_long, lastest_ema_long)
          
            

    # 组合择时指标 (实时）
    def select_Time_Mix(self, conditionBuy = 2, conditonSale = 2):
        
        # 综合策略
        signalMA = self.select_Time_MA()
        signalMACD = self.select_Time_MACD()
        signalDMA = self.select_Time_DMA()
        signalTRIX = self.select_Time_TRIX()
        signalAMA = self.select_Time_AMA()
        
        # 买入信号的总数
        buyTotal = (abs(signalMA)+signalMA)/2 + (abs(signalMACD)+signalMACD)/2 + \
                 (abs(signalDMA)+signalDMA)/2 + (abs(signalTRIX)+signalTRIX)/2 + (abs(signalAMA)+signalAMA)/2 
                 
        # 卖出信号的总数
        saleTotal = (-abs(signalMA)+signalMA)/2 + (-abs(signalMACD)+signalMACD)/2 + \
                 (-abs(signalDMA)+signalDMA)/2 + (-abs(signalTRIX)+signalTRIX)/2 + (-abs(signalAMA)+signalAMA)/2
        
        signal = SIGNAL_DEFAULT
        if buyTotal+saleTotal >= conditionBuy:
            signal = SIGNAL_BUY
        elif buyTotal+saleTotal <= -conditonSale:
            signal = SIGNAL_SALE
        
        return signal 
    
    # MA指标择时  (回测）
    def select_Time_MA(self):
        
        #EMA 
        ma_list = [self.AVR_SHORT, self.AVR_LONG]
        if ma_list[0] == self.AVR_SHORT and ma_list[1] == self.AVR_LONG:
            ema_close_short = self.ma_short
            ema_close_long = self.ma_long
        else:     
            ema_close_short = pd.rolling_mean(self.close_price, ma_list[0])
            ema_close_long = pd.rolling_mean(self.close_price, ma_list[1])
        
        
        signal = SIGNAL_DEFAULT
        
        if ema_close_short[-1] > ema_close_short[-2] and ema_close_short[-1] > ema_close_long[-1] \
                            and ema_close_short[-2] < ema_close_long[-2]:
            signal = SIGNAL_BUY
        elif ema_close_long[-1] < ema_close_long[-2] and ema_close_short[-1] < ema_close_long[-1] \
                            and ema_close_short[-2] > ema_close_long[-2]:
            signal = SIGNAL_SALE            
        
        return signal            
            
        
    # MACD指标择时 (回测）
    def select_Time_MACD(self):
        
        #EMA 
        ma_list = [self.AVR_SHORT, self.AVR_LONG]
        ma_dea = 10
        if ma_list[0] == self.AVR_SHORT and ma_list[1] == self.AVR_LONG:
            ema_close_short = self.ema_short
            ema_close_long = self.ema_long
        else:     
            ema_close_short = pd.ewma(self.close_price, span=ma_list[0])
            ema_close_long = pd.ewma(self.close_price, span=ma_list[1])
        
        
        dif_price = ema_close_short - ema_close_long
        dea_price = pd.ewma(dif_price, span=ma_dea)
        macd_price = 2 * (dif_price - dea_price)
        
        signal = SIGNAL_DEFAULT
            
        if dif_price[-1] > dif_price[-2] and dif_price[-1] > dea_price[-2] \
                                            and dif_price[-2] < dea_price[-2] and dea_price[-1] > 0:
            signal = SIGNAL_BUY
        elif dif_price[-1] < dif_price[-2] and dif_price[-1] < dea_price[-1] \
                            and dif_price[-2] > dea_price[-2] and dif_price[-1] < 0:
            signal = SIGNAL_SALE            
        return signal            
    
    # DMA指标择时 (回测）
    def select_Time_DMA(self):
        
        #MA 
        ma_list = [self.AVR_SHORT, self.AVR_LONG]
        ma_dea = 10
        
        if ma_list[0] == self.AVR_SHORT and ma_list[1] == self.AVR_LONG:
            ma_close_short = self.ma_short
            ma_close_long = self.ma_long
        else:    
            ma_close_short = pd.rolling_mean(self.close_price, ma_list[0])
            ma_close_long = pd.rolling_mean(self.close_price, ma_list[1])
        
        dma_price = ma_close_short - ma_close_long
        ama_price = pd.rolling_mean(dma_price, ma_dea)
        
        signal = SIGNAL_DEFAULT
            
        if dma_price[-1] > dma_price[-2] and dma_price[-1] > ama_price[-1] \
                                            and dma_price[-2] < ama_price[-2]:
            signal = SIGNAL_BUY
        elif dma_price[-1] < dma_price[-2] and dma_price[-1] < ama_price[-1] \
                            and dma_price[-2] > ama_price[-2]:
            signal = SIGNAL_SALE           
        return signal            
        
     
    # TRIX指标择时 (回测）
    def select_Time_TRIX(self):
        
        #EMA 
        ma_list = [self.AVR_SHORT, self.AVR_SHORT] #N,M
        
        if ma_list[0] == self.AVR_SHORT:
            ema_close = self.ema_short
        else:    
            ema_close = pd.ewma(self.close_price, span=ma_list[0])
        ema_close = pd.ewma(ema_close, span=ma_list[0])
        tr_close = pd.ewma(ema_close, span=ma_list[0])
        
        trixsList = [0]
        for i in range(1, len(tr_close)):
            #print tr_close[i], tr_close[i-1]
            trix = (tr_close[i]-tr_close[i-1])/tr_close[i-1]*100
            trixsList.append(trix)
        trixs = np.array(trixsList)    
        maxtrix = pd.rolling_mean(trixs, ma_list[1])
        
        signal = SIGNAL_DEFAULT
            
        if trixs[-1] > trixs[-2] and trixs[-1] > maxtrix[-1] \
                                            and trixs[-2] < maxtrix[-2]:
            signal = SIGNAL_BUY
        elif trixs[-1] < trixs[-2] and trixs[-1] < maxtrix[-1] \
                            and trixs[-2] > maxtrix[-2]:
            signal = SIGNAL_SALE            
        return signal
    
            
       
    
    # AMA指标择时
    def select_Time_AMA(self):
        
        percentage = 0.1
        
        # 指数平滑序列
        containts = [0]*10
        for i in range(10, len(self.close_price)):
            sub_price = self.close_price[i-10:i]
            constaint = self.getConstaint(sub_price)
            containts.append(constaint);
            
        ama_price = [float(self.close_price[0])]    
        for i in range(1, len(self.close_price)):
            ama = containts[i-1] * float(self.close_price[i-1]) + (1-containts[i-1])*ama_price[i-1]
            ama_price.append(float(ama))
         
        #print np.array(ama_price[i-19:i+1]) - np.array(ama_price[i-20:i])
        threshold = percentage * np.std(np.array(ama_price[i-19:i+1]) - np.array(ama_price[i-20:i])) # 过滤器
        
        signal = SIGNAL_DEFAULT
        if ama_price[-1] - np.min(ama_price[-6:-1]) > threshold: 
            signal = SIGNAL_BUY
        elif np.max(ama_price[-6:-1]) - ama_price[-1] > threshold:    
            signal = SIGNAL_SALE    
            
        return signal
    
    # 获取平方平滑系数
    def getConstaint(self, prices):
        direction = abs(float(prices[-1]) - float(prices[0]))
        volatility = sum(abs(float(prices[i+1])-float(prices[i])) for i in range(len(prices)-1))
        if volatility == 0.0:
            return 0
        ER = abs(direction/volatility)   
        fastSC = 2.0/(2.0+1)
        slowSC = 2.0/(30.0+1)
        sSC = ER * (fastSC-slowSC) + slowSC
        constaint = sSC*sSC 
        return constaint

