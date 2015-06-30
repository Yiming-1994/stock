#!/usr/local/bin/python
#coding=utf-8

from sqlalchemy import create_engine
import tushare as ts
import os
import pandas as pd
import datetime
from multiprocessing.dummy import Pool as ThreadPool
from tushare.util import dateu as du
from pandas.core.algorithms import mode
from util import stockutil as util
import util.commons as cm
import redis

#DB_WAY:数据存储方式 'csv'  # or 'mysql'
DB_WAY = 'csv'
DB_USER = 'root'
DB_PWD = '1234' # or '123456' in win7
DB_NAME = 'test'


###################################
#-- 获取股票基本信息       --#
############################
# 通过DB_WAY 选择存入csv或mysql
def download_stock_basic_info():
    
    try:
        df = ts.get_stock_basics()
        #直接保存
        if DB_WAY == 'csv':
            print 'choose csv'
            df.to_csv(cm.DownloadDir+cm.TABLE_STOCKS_BASIC + '.csv');
            print 'download csv finish'
            
        elif DB_WAY == 'mysql':
            print 'choose mysql'
            engineString = 'mysql://' + DB_USER + ':' + DB_PWD + '@127.0.0.1/' + DB_NAME + '?charset=utf8'
            print engineString
            engine = create_engine(engineString)
            
            df.to_sql(cm.TABLE_STOCKS_BASIC, engine, if_exists='replace')
            
            sql = 'select * from ' + cm.TABLE_STOCKS_BASIC + ' where code = "600000"'
            dfRead = pd.read_sql(sql, engine)
            print dfRead
    except Exception as e:
        print str(e)        

# 下载股票的K线
# code:股票代码
# 默认为前复权数据：open, high, close, low； 不复权数据为：open_no_fq等，后复权数据为：open_hfq
# 默认为上市日期到今天的K线数据
def download_stock_kline(code, date_start='', date_end=datetime.date.today()):
    code = util.getSixDigitalStockCode(code)
    
    try:
        fileName = 'h_kline_' + str(code) + '.csv'
        
        writeMode = 'w'
        if os.path.exists(cm.DownloadDir+fileName):
            #print (">>exist:" + code)
            df = pd.DataFrame.from_csv(path=cm.DownloadDir+fileName)
            
            se = df.head(1).index #取已有文件的最近日期
            dateNew = se[0] + datetime.timedelta(1)
            date_start = dateNew.strftime("%Y-%m-%d")
            #print date_start
            writeMode = 'a'
        
        if date_start == '':
            se = get_stock_info(code)
            date_start = se['timeToMarket'] 
            date = datetime.datetime.strptime(str(date_start), "%Y%m%d")
            date_start = date.strftime('%Y-%m-%d')
        date_end = date_end.strftime('%Y-%m-%d')  
        
        # 已经是最新的数据
        if date_start >= date_end:
            df = pd.read_csv(cm.DownloadDir+fileName)
            return df
        
        print 'download ' + str(code) + ' k-line >>>begin (', date_start+u' 到 '+date_end+')'
        df_qfq = ts.get_h_data(str(code), start=date_start, end=date_end) # 前复权
        df_nfq = ts.get_h_data(str(code), start=date_start, end=date_end) # 不复权
        df_hfq = ts.get_h_data(str(code), start=date_start, end=date_end) # 后复权
        
        if df_qfq is None or df_nfq is None or df_hfq is None:
            return None
        
        df_qfq['open_no_fq'] = df_nfq['open']
        df_qfq['high_no_fq'] = df_nfq['high']
        df_qfq['close_no_fq'] = df_nfq['close']
        df_qfq['low_no_fq'] = df_nfq['low']
        df_qfq['open_hfq']=df_hfq['open']
        df_qfq['high_hfq']=df_hfq['high']
        df_qfq['close_hfq']=df_hfq['close']
        df_qfq['low_hfq']=df_hfq['low']
        
        if writeMode == 'w':
            df_qfq.to_csv(cm.DownloadDir+fileName)
        else:
            
            df_old = pd.DataFrame.from_csv(cm.DownloadDir + fileName)
            
            # 按日期由远及近
            df_old = df_old.reindex(df_old.index[::-1])
            df_qfq = df_qfq.reindex(df_qfq.index[::-1])
            
            df_new = df_old.append(df_qfq)
            #print df_new
            
            # 按日期由近及远
            df_new = df_new.reindex(df_new.index[::-1])
            df_new.to_csv(cm.DownloadDir+fileName)
            #df_qfq = df_new
            
        print '\ndownload ' + str(code) +  ' k-line finish'
        return pd.read_csv(cm.DownloadDir+fileName)
        
    except Exception as e:
        print str(e)        
    
        
    return None

# 下载股票的历史分笔数据
# code:股票代码
# 默认为最近3年的分笔数据
def download_stock_quotes(code, date_start='', date_end=str(datetime.date.today())):
    code = util.getSixDigitalStockCode(code)
    try:
        if date_start == '':
            date = datetime.datetime.today().date() + datetime.timedelta(-365*3) 
            date_start = str(date)
          
        dateStart = datetime.datetime.strptime(str(date_start), "%Y-%m-%d")   
                
        for i in range(du.diff_day(date_start, date_end)):
            date = dateStart + datetime.timedelta(i)
            strDate = date.strftime("%Y-%m-%d")
            df = ts.get_tick_data(code, strDate)
            print df
    except Exception as e:
        print str(e)        

#######################
##  private methods  ##
#######################

# 获取个股的基本信息：股票名称，行业，地域，PE等，详细如下
#     code,代码
#     name,名称
#     industry,所属行业
#     area,地区
#     pe,市盈率
#     outstanding,流通股本
#     totals,总股本(万)
#     totalAssets,总资产(万)
#     liquidAssets,流动资产
#     fixedAssets,固定资产
#     reserved,公积金
#     reservedPerShare,每股公积金
#     eps,每股收益
#     bvps,每股净资
#     pb,市净率
#     timeToMarket,上市日期
# 返回值类型：Series
def get_stock_info(code):
    if DB_WAY == 'csv':
        try:
            df = pd.DataFrame.from_csv(cm.DownloadDir + cm.TABLE_STOCKS_BASIC + '.csv')
            #se = df.loc[int(code)]
            se = df.ix[int(code)]
            return se
        except Exception as e:
            #print str(e)
            return None
                

# 获取所有股票的历史K线
def download_all_stock_history_k_line():
    print 'download all stock k-line'
    if DB_WAY == 'csv':
        try:
            df = pd.DataFrame.from_csv(cm.DownloadDir + cm.TABLE_STOCKS_BASIC + '.csv')
            #se = df.loc[int(code)]
            #se = df.ix[code]
            pool = ThreadPool(processes=1)
            pool.map(download_stock_kline, df.index)
            pool.close()
            pool.join()  
            
        except Exception as e:
            print str(e)
    print 'download all stock k-line'
    
class DataBase:
    def __init__(self):
        self.host = 'localhost'
        self.port = 6379
        self.write_pool = {}  
        
    def write(self,website,city,year,month,day,deal_number):  
        try:  
            key = '_'.join([website,city,str(year),str(month),str(day)])  
            val = deal_number  
            r = redis.StrictRedis(host=self.host,port=self.port)  
            r.set(key,val)  
        except Exception, exception:  
            print exception  

    def read(self,website,city,year,month,day):  
        try:  
            key = '_'.join([website,city,str(year),str(month),str(day)])  
            r = redis.StrictRedis(host=self.host,port=self.port)  
            value = r.get(key)  
            print value  
            return value  
        except Exception, exception:  
            print exception    
    
    def add_write(self,website,city,year,month,day,deal_number):  
        key = '_'.join([website,city,str(year),str(month),str(day)])  
        val = deal_number  
        self.write_pool[key] = val  

    def batch_write(self):  
        try:  
            r = redis.StrictRedis(host=self.host,port=self.port)  
            r.mset(self.write_pool)  
        except Exception, exception:  
            print exception

def add_data():  
    beg = datetime.datetime.now()  
    db = DataBase()  
    for i in range(1,10000):  
        db.add_write('meituan','beijing',2013,i,1,i)  
    db.batch_write()  
    end = datetime.datetime.now()  
    print end-beg             
            
if __name__ == '__main__'  :
    add_data()    
#     db = DataBase()  
#     db.write('meituan','beijing',2013,9,1,8000)  
#     db.read('meituan','beijing',2013,9,1)  
    #download_stock_basic_info()
    #get_single_stock_info(600000)
    #download_all_stock_history_k_line()
    #download_stock_quotes(600000)
    #download_stock_kline('002767')


