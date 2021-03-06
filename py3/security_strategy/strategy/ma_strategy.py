

import pandas as pd
import numpy as np

from init import *
from util.date_convert import GetNowDate

class MAStrategy:
    """
    实时均线策略
    """

    def __init__(self, trade, df_close, avr_short, avr_long):
        """
        :param code:  股票代码
        :param trade:  实时股价, float
        :param df_close: 收盘价序列,已排序, columns=['date', 'close']
        """
        
        self.AVR_SHORT = avr_short
        self.AVR_LONG = avr_long
        self.MA_DEA = 10

        self.COL_MA_S = 'ma_{}'.format(self.AVR_SHORT)
        self.COL_MA_L = 'ma_{}'.format(self.AVR_LONG)
        self.COL_EMA_S = 'ema_{}'.format(self.AVR_SHORT)
        self.COL_EMA_L = 'ema_{}'.format(self.AVR_LONG)

        df_close = self.calcute_ma(df_close, AVR_SHORT, AVR_LONG)

        if trade: #有实时股价
            df_now = df_close.tail(1).copy()
            df_now['date'] = GetNowDate()
            df_now['close'] = trade
            df_close = pd.concat([df_close, df_now], ignore_index=True)
            # print df_close.tail()

        #计算当前日期的ma
        lastest_ma_short = sum(df_close['close'][-self.AVR_SHORT:])/self.AVR_SHORT
        lastest_ma_long = sum(df_close['close'][-self.AVR_LONG:])/self.AVR_LONG

        df_last = df_close[-1:]
        df_last[self.COL_MA_S] = lastest_ma_short
        df_last[self.COL_MA_L] = lastest_ma_long


        #计算当前的ema
        lastest_ema_short = df_close[self.COL_EMA_S].get_values()[-2] * (self.AVR_SHORT-1)/(self.AVR_SHORT+1) + trade * 2 /(self.AVR_SHORT+1)
        lastest_ema_long = df_close[self.COL_EMA_L].get_values()[-2] * (self.AVR_LONG-1)/(self.AVR_LONG+1) + trade * 2 /(self.AVR_LONG+1)

        df_last[self.COL_EMA_S] = lastest_ema_short
        df_last[self.COL_EMA_L] = lastest_ema_long

        self.df_close = df_close

        # print self.df_close.head()
        # print self.df_close.tail()
          

    def select_Time_Mix(self, conditionBuy = 2, conditonSale = 2):
        """
        组合择时指标 (实时）
        :param conditionBuy: 满足2个即买入
        :param conditonSale: 满足2个即卖出
        :return:
        """
        
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
    
    # MA指标择时
    def select_Time_MA(self):
        
        #DMA
        dma_close_short = self.df_close[self.COL_MA_S].get_values()
        dma_close_long = self.df_close[self.COL_MA_L].get_values()
        
        
        signal = SIGNAL_DEFAULT
        
        if dma_close_short[-1] > dma_close_short[-2] and dma_close_short[-1] > dma_close_long[-1] \
                            and dma_close_short[-2] < dma_close_long[-2]:
            signal = SIGNAL_BUY
        elif dma_close_long[-1] < dma_close_long[-2] and dma_close_short[-1] < dma_close_long[-1] \
                            and dma_close_short[-2] > dma_close_long[-2]:
            signal = SIGNAL_SALE            
        
        return signal            
            
        
    # MACD指标择时
    def select_Time_MACD(self):
        
        #EMA
        # print self.df_close.tail()
        ema_close_short = self.df_close[self.COL_EMA_S].get_values()
        ema_close_long = self.df_close[self.COL_EMA_L].get_values()

        
        dif_price = ema_close_short - ema_close_long
        dea_price = pd.ewma(dif_price, span=self.MA_DEA)
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

        # DMA
        ma_close_short = self.df_close[self.COL_MA_S].get_values()
        ma_close_long = self.df_close[self.COL_MA_L].get_values()
        
        # #MA
        # ma_list = [self.AVR_SHORT, self.AVR_LONG]
        # ma_dea = 10
        #
        # if ma_list[0] == self.AVR_SHORT and ma_list[1] == self.AVR_LONG:
        #     ma_close_short = self.ma_short
        #     ma_close_long = self.ma_long
        # else:
        #     ma_close_short = pd.rolling_mean(self.close_price, ma_list[0])
        #     ma_close_long = pd.rolling_mean(self.close_price, ma_list[1])
        
        dma_price = ma_close_short - ma_close_long
        ama_price = pd.rolling_mean(dma_price, self.MA_DEA)
        
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
        ema_close_short = self.df_close[self.COL_EMA_S].get_values()
        ema_ema_close_short = pd.ewma(ema_close_short, span=self.AVR_SHORT)
        tr_close = pd.ewma(ema_ema_close_short, span=self.AVR_SHORT)

        # ma_list = [self.AVR_SHORT, self.AVR_SHORT] #N,M
        #
        # if ma_list[0] == self.AVR_SHORT:
        #     ema_close = self.ema_short
        # else:
        #     ema_close = pd.ewma(self.close_price, span=ma_list[0])
        # ema_close = pd.ewma(ema_close, span=ma_list[0])
        # tr_close = pd.ewma(ema_close, span=ma_list[0])
        
        trixsList = [0]
        for i in range(1, len(tr_close)):
            #print tr_close[i], tr_close[i-1]
            trix = (tr_close[i]-tr_close[i-1])/tr_close[i-1]*100
            trixsList.append(trix)
        trixs = np.array(trixsList)    
        maxtrix = pd.rolling_mean(trixs, self.AVR_LONG)
        
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

        close_price = self.df_close['close'].get_values()
        
        # 指数平滑序列
        containts = [0]*10
        for i in range(10, len(close_price)):
            sub_price = close_price[i-10:i]
            constaint = self._getConstaint(sub_price)
            containts.append(constaint)
            
        ama_price = [float(close_price[0])]
        for i in range(1, len(close_price)):
            ama = containts[i-1] * float(close_price[i-1]) + (1-containts[i-1])*ama_price[i-1]
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
    def _getConstaint(self, prices):
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

    def calcute_ma(self, df, avr_short=12, avr_long=40):
        """
        计算ma, ema
        :param df:
        :return:
        """
        if len(df) == 0:
            return

        # print "{} calcute ma".format(df.ix[0,'code'])
        df['ma_' + str(avr_short)] = pd.rolling_mean(df['close'], avr_short)  # 12
        df['ma_' + str(avr_long)] = pd.rolling_mean(df['close'], avr_long)  # 40

        # print "{} calcute ema".format(df.ix[0, 'code'])
        df['ema_' + str(avr_short)] = pd.ewma(df['close'], span=avr_short)  # 12
        df['ema_' + str(avr_long)] = pd.ewma(df['close'], span=avr_long)  # 40

        df = df.replace(np.nan, 0)
        return df