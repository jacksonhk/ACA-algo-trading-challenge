



from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.arr_close = numpy.array([])
        self.arr_fastMA = numpy.array([])
        self.arr_midMA = numpy.array([])
        self.arr_slowMA = numpy.array([])
        self.arr_LongTermMA = numpy.array([])
        
        self.fastperiod = 5
        self.midperiod = 8
        self.slowperiod = 13
        self.longperiod = 50
        
        self.highprice = numpy.array([])
        self.lowprice = numpy.array([])
        self.atr_period = 14
        self.general_period = 14
        
        self.openOrder = {}
        self.netOrder = {}

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours = 6):
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            lastprice = bd[self.myinstrument]['lastPrice']
            self.arr_close = numpy.append(self.arr_close, lastprice)
            self.highprice = numpy.append(self.highprice, bd[self.myinstrument]['highPrice'])
            self.lowprice = numpy.append(self.lowprice, bd[self.myinstrument]['lowPrice'])
            # keep the most recent observations
            time_period = self.fastperiod + self.midperiod + self.slowperiod + 1
            if len(self.arr_close) > time_period:
                self.arr_close = self.arr_close[-time_period:]
                
            # keep the most recent observations
            if len(self.highprice)>=self.atr_period:
                self.highprice = self.highprice[-time_period:]
            # keep the most recent observations
            if len(self.lowprice)>=self.atr_period:
                self.lowprice = self.lowprice[-time_period:]
                
            # fit SMA line
            self.arr_fastMA = talib.DEMA(self.arr_close, timeperiod=int(self.fastperiod))
            self.arr_midMA = talib.DEMA(self.arr_close, timeperiod=int(self.midperiod))
            self.arr_slowMA = talib.DEMA(self.arr_close, timeperiod=int(self.slowperiod))
            # debug print result
            self.evt.consoleLog("arr_fastMA=", self.arr_fastMA)
            self.evt.consoleLog("arr_midMA=", self.arr_midMA)
            self.evt.consoleLog("arr_slowMA=", self.arr_slowMA)
            
            atr = talib.ATR(self.highprice, self.lowprice, self.arr_close, timeperiod=self.atr_period)
            self.evt.consoleLog("atr=", atr[-1])
            
            self.evt.consoleLog("highprice=", self.highprice)
            self.evt.consoleLog("lowprice=", self.lowprice)
            self.evt.consoleLog("arr_close=", self.arr_close[-self.atr_period:])
            stoploss = 2.0 * atr[-1]
            
            # Long EMA as a momentum indicator:
            self.arr_LongTermMA = talib.EMA(self.arr_close, timeperiod=int(self.longperiod))
            price_above_longtermMA = self.arr_close[-1] >= self.arr_LongTermMA[-1] 
            LongTermEMA_rising = False
            price_cross_above_longtermMA = False
            price_cross_below_longtermMA = False
            if len(self.arr_LongTermMA) > 1:
                LongTermEMA_rising = self.arr_LongTermMA[-1] >= self.arr_LongTermMA[-2]
                price_cross_above_longtermMA = self.arr_close[-1] >= self.arr_LongTermMA[-1] and self.arr_close[-2] <= self.arr_LongTermMA[-2]
                price_cross_below_longtermMA = self.arr_close[-1] <= self.arr_LongTermMA[-1] and self.arr_close[-2] >= self.arr_LongTermMA[-2]
            
            # Calculate the ADXR using talib.ADXR
            adxr = talib.ADXR(self.highprice, self.lowprice, self.arr_close, timeperiod=self.general_period)
            
            # Caclulate the APO for momentum detection
            apo = talib.APO(self.arr_close, self.midperiod, self.slowperiod)
            
            macd, signal, hist = talib.MACD(self.arr_close, self.fastperiod, self.slowperiod, self.midperiod)
            
            # Calculate Aroon values
            aroon_up, aroon_down = talib.AROON(self.highprice, self.lowprice, timeperiod=self.general_period)
            aroonosc = aroon_up - aroon_down
            
            self.evt.consoleLog("ADXR=", adxr[-1])
            ranging = self.rangingFilter(adxr[-1], aroonosc[-1])
            bullish = self.momentumFilter(apo[-1], macd, aroonosc, price_above_longtermMA, LongTermEMA_rising)
            nav = ab['NAV']
            
            # 5-8-13 EMA crossover implementation: Note: poor performance during ranging market
            # check number of record is at least greater than both self.fastperiod, self.slowperiod
            if not numpy.isnan(self.arr_fastMA[-1]) and not numpy.isnan(self.arr_fastMA[-2]) and not numpy.isnan(self.arr_slowMA[-1]) and not numpy.isnan(self.arr_slowMA[-2]) and not numpy.isnan(self.arr_midMA[-1]) and not numpy.isnan(self.arr_midMA[-2]):
                # send a buy order for Golden Cross (fastMA above slowMA, midMA crosses above slowMA)
                if (not ranging and bullish == 1) and ((self.arr_fastMA[-1] > self.arr_slowMA[-1] and self.arr_midMA[-1] > self.arr_slowMA[-1] and self.arr_midMA[-2] < self.arr_slowMA[-2]) or price_cross_above_longtermMA):
                    self.closeAllOrder()
                    volume = self.find_positionSize(lastprice, nav)
                    self.test_sendOrder(lastprice, 1, 'open', volume, stoploss)
                # send a sell order for Death Cross
                if (not ranging and bullish == -1) and ((self.arr_fastMA[-1] < self.arr_slowMA[-1] and self.arr_midMA[-1] < self.arr_slowMA[-1] and self.arr_midMA[-2] > self.arr_slowMA[-2]) or price_cross_below_longtermMA):
                    self.closeAllOrder()
                    volume = self.find_positionSize(lastprice, nav)
                    self.test_sendOrder(lastprice, -1, 'open', volume, stoploss)
            
            # TODO: Average up (increase stake) logic: throwback and pullback handling for 
            
            
            # TODO: Ranging market filtering indicator
            
            # update takeprofit and stoploss point dynamically
            if self.openOrder:
                self.update_stoploss(stoploss)

    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        pass

    def on_openPositionfeed(self, op, oo, uo):
        self.openOrder = oo
        self.netOrder = op
    
    def rangingFilter(self, ADXR, AROONOsc):
        if ADXR < 20 or abs(AROONOsc) < 30:
            return True # ranging market
        else:
            return False
    
    def momentumFilter(self, APO, MACD, AROONOsc, price_above_longtermMA, LongTermEMA_rising):
        # macd rising check
        MACDRising = False
        if numpy.isnan(MACD[-1]) or numpy.isnan(MACD[-2]):
            MACDRising = False
        elif int(MACD[-1]) > int(MACD[-2]):
            MACDRising = True
        
        # aroonosc rising check
        AROON_direction = 0 # not moving
        if numpy.isnan(AROONOsc[-1]) or numpy.isnan(AROONOsc[-2]):
            AROON_direction = 0
        elif int(AROONOsc[-1]) > int(AROONOsc[-2]):
            AROON_direction = 1 # moving upwawrds
        elif int(AROONOsc[-1]) < int(AROONOsc[-2]):
            AROON_direction = -1 # moving downwards
        else:
            AROON_direction = 0 # not moving
        
        AROON_positive = False
        if numpy.isnan(AROONOsc[-1]):
            AROON_positive = False
        elif int(AROONOsc[-1]) > 0:
            AROON_positive = True
            
        if APO > 0 and (MACDRising or AROON_direction == 1 or AROON_positive) and (price_above_longtermMA or LongTermEMA_rising) :
            return 1 # Bullish 
            
        elif APO < 0 and (not MACDRising or AROON_direction == -1 or not AROON_positive) and (not price_above_longtermMA or not LongTermEMA_rising):
            return -1 # Bearish
        else:
            return 0 # Neutral
    
    def test_sendOrder(self, lastprice, buysell, openclose, volume, stoploss):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell==1: # buy order
            order.takeProfitLevel = lastprice + 2.0 * stoploss
            order.stopLossLevel = lastprice - stoploss
        elif buysell==-1:
            order.takeProfitLevel = lastprice - 2.0 * stoploss
            order.stopLossLevel = lastprice + stoploss
        order.volume = volume
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)
    
    def closeAllOrder(self):
        if not self.openOrder:
            return False
        for ID in self.openOrder:
            order = AlgoAPIUtil.OrderObject(
                tradeID = ID,
                openclose = 'close',
                instrument = self.myinstrument,
            )
            self.evt.sendOrder(order)
        return True
    
    # ATR trailing stop implementation
    def update_stoploss(self, new_stoploss):
        for ID in self.openOrder:
            openPosition = self.openOrder[ID]
            if openPosition['buysell'] == 1 and openPosition['stopLossLevel'] < openPosition['openprice'] - new_stoploss: 
                # for buy ordder, update stop loss if current ATR stop is higher than previous 
                res = self.evt.update_opened_order(tradeID=ID, sl = openPosition['openprice'] - new_stoploss)
                # update the update stop loss using ATR stop
            elif openPosition['buysell'] == -1 and openPosition['openprice'] + new_stoploss < openPosition['stopLossLevel']: 
                # for buy ordder, update stop loss if current ATR stop is higher than previous 
                res = self.evt.update_opened_order(tradeID=ID, sl = openPosition['openprice'] + new_stoploss)
                # update the update stop loss using ATR stop
    
    # utility function to find volume based on available balance
    def find_positionSize(self, lastprice, nav):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        ratio = 0.9
        volume = (nav*ratio) / lastprice
        total =  volume * lastprice
        while total < 0.9 * nav:
            ratio *= 1.05
            volume = (nav*ratio) / lastprice
            total =  volume * lastprice
        while total > 0.9 * availableBalance:
            ratio *= 0.95
            volume = (nav*ratio) / lastprice
            total =  volume * lastprice
        return volume
    


Performance:
Annual Sharpe Ratio: 1.433
Annual Sortino Ratio:	3.0935
Return on 6-month: 12.65%




