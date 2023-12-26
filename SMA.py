from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.arr_close = numpy.array([])
        self.arr_fastMA = numpy.array([])
        self.arr_slowMA = numpy.array([])
        self.fastperiod = 7
        self.slowperiod = 14
        
        self.highprice = numpy.array([])
        self.lowprice = numpy.array([])
        self.atr_period = 14

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours=24):
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            lastprice = bd[self.myinstrument]['lastPrice']
            self.arr_close = numpy.append(self.arr_close, lastprice)
            self.highprice = numpy.append(self.highprice, bd[self.myinstrument]['highPrice'])
            self.lowprice = numpy.append(self.lowprice, bd[self.myinstrument]['lowPrice'])
            # keep the most recent observations
            if len(self.arr_close)>int(self.fastperiod+self.slowperiod):
                self.arr_close = self.arr_close[-int(self.fastperiod+self.slowperiod):]
            # keep the most recent observations
            if len(self.highprice)>self.atr_period:
                self.highprice = self.highprice[-self.atr_period:]
            # keep the most recent observations
            if len(self.lowprice)>self.atr_period:
                self.lowprice = self.lowprice[-self.atr_period:]
                
            # fit SMA line
            self.arr_fastMA = talib.SMA(self.arr_close, timeperiod=int(self.fastperiod))
            self.arr_slowMA = talib.SMA(self.arr_close, timeperiod=int(self.slowperiod))
            # debug print result
            self.evt.consoleLog("arr_fastMA=", self.arr_fastMA)
            self.evt.consoleLog("arr_slowMA=", self.arr_slowMA)
            
            atr = talib.ATR(self.highprice, self.lowprice, self.arr_close[-self.atr_period:], timeperiod=int(self.atr_period))
            
            
            # check number of record is at least greater than both self.fastperiod, self.slowperiod
            if not numpy.isnan(self.arr_fastMA[-1]) and not numpy.isnan(self.arr_fastMA[-2]) and not numpy.isnan(self.arr_slowMA[-1]) and not numpy.isnan(self.arr_slowMA[-2]):
                # send a buy order for Golden Cross
                volume = self.tune_positionSize(lastprice)
                stoploss = 2 * atr
                if self.arr_fastMA[-1] > self.arr_slowMA[-1] and self.arr_fastMA[-2] < self.arr_slowMA[-2]:
                    self.test_sendOrder(lastprice, 1, 'open', volume, stoploss)
                # send a sell order for Death Cross
                if self.arr_fastMA[-1] < self.arr_slowMA[-1] and self.arr_fastMA[-2] > self.arr_slowMA[-2]:
                    self.test_sendOrder(lastprice, -1, 'open', volume, stoploss)

    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        pass

    def on_openPositionfeed(self, op, oo, uo):
        self.openOrder = oo
        self.netOrder = op

    def test_sendOrder(self, lastprice, buysell, openclose, volume, stoploss):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell==1:
            order.takeProfitLevel = lastprice*1.1
            order.stopLossLevel = lastprice - stoploss
        elif buysell==-1:
            order.takeProfitLevel = lastprice*0.9
            order.stopLossLevel = lastprice + stoploss
        order.volume = volume
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)
    
    def tune_positionSize(self, lastprice):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        Y_ratio = 0.5
        Y_position = (availableBalance*Y_ratio) / lastprice
        total =  availableBalance*Y_ratio
        while total < 0.8 * availableBalance:
            Y_ratio *= 1.05
            Y_position = (availableBalance*Y_ratio) / lastprice
            total = availableBalance*Y_ratio
        while total > availableBalance:
            Y_ratio *= 0.95
            Y_position = (availableBalance*Y_ratio) / lastprice
            total = availableBalance*Y_ratio
        return Y_position
    
