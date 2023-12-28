



from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib, numpy

class AlgoEvent:
    def __init__(self):
        
        self.fastperiod = 5
        self.midperiod = 8
        self.slowperiod = 13
        self.longperiod = 50
        self.atr_period = 14
        self.general_period = 14
        self.instrument_data = {}
        self.openOrder = {}
        self.netOrder = {}
        self.lasttradetime = datetime(2000,1,1)

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.no_instrument = len(mEvt['subscribeList'])
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        # adding data for each instrument on every data received
        if isSync:
            if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours = 6): 
                self.lasttradetime = bd[self.myinstrument]['timestamp']
                # update trade time if timeframe match and continue the code
            else:
                return # do not trade if timeframe does not match
            for instrument in bd:
                if instrument not in self.instrument_data:
                    self.instrument_data[instrument] = {
                        'arr_close': numpy.array([]),
                        'arr_fastMA': numpy.array([]),
                        'arr_midMA': numpy.array([]),
                        'arr_slowMA': numpy.array([]),
                        'arr_LongTermMA': numpy.array([]),
                        'highprice': numpy.array([]),
                        'lowprice': numpy.array([]),
                        'lasttradetime': datetime(2000,1,1),
                        'atr': numpy.array([]),
                        'stoploss': 0,
                        'entry_signal': 0 # 1 == long, -1 == short, 0 == No signal
                    }
                
                instrument_data = self.instrument_data[instrument]
                lastprice = bd[instrument]['lastPrice']
                instrument_data['arr_close'] = numpy.append(instrument_data['arr_close'], lastprice)
                instrument_data['highprice'] = numpy.append(instrument_data['highprice'], bd[instrument]['highPrice'])
                instrument_data['lowprice'] = numpy.append(instrument_data['lowprice'], bd[instrument]['lowPrice'])
                # keep the most recent observations
                time_period = (
                    self.fastperiod + self.midperiod + self.slowperiod + 1
                )
                    
                if len(instrument_data['arr_close']) > time_period:
                    instrument_data['arr_close'] = instrument_data['arr_close'][-time_period:]
                        
                # keep the most recent observations
                if len(instrument_data['highprice']) >= time_period:
                    instrument_data['highprice'] = instrument_data['highprice'][-time_period:]
                # keep the most recent observations
                if len(instrument_data['lowprice']) >= time_period:
                    instrument_data['lowprice'] = instrument_data['lowprice'][-time_period:]
                    
                # fit SMA line
                instrument_data['arr_fastMA'] = talib.DEMA(
                    instrument_data['arr_close'], timeperiod=self.fastperiod
                )
                instrument_data['arr_midMA'] = talib.DEMA(
                    instrument_data['arr_close'], timeperiod=self.midperiod
                )
                instrument_data['arr_slowMA'] = talib.DEMA(
                    instrument_data['arr_close'], timeperiod=self.slowperiod
                )
                    
                instrument_data['atr'] = talib.ATR(
                    instrument_data['highprice'],
                    instrument_data['lowprice'],
                    instrument_data['arr_close'],
                    timeperiod=self.atr_period
                )
                    
                instrument_data['stoploss'] = 2.0 * instrument_data['atr'][-1]
                # Long EMA as a momentum indicator:
                instrument_data['arr_LongTermMA'] = talib.EMA(instrument_data['arr_close'], timeperiod=self.longperiod)
                    
                # checking for entry signal
                price_above_longtermMA = instrument_data['arr_close'][-1] >= instrument_data['arr_LongTermMA'][-1] 
                LongTermEMA_rising = False
                price_cross_above_longtermMA = False
                price_cross_below_longtermMA = False
                    
                if len(instrument_data['arr_LongTermMA']) > 1:
                    LongTermEMA_rising = instrument_data['arr_LongTermMA'][-1] >= instrument_data['arr_LongTermMA'][-2]
                    price_cross_above_longtermMA = instrument_data['arr_close'][-1] >= instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_close'][-2] <= instrument_data['arr_LongTermMA'][-2]
                    price_cross_below_longtermMA = instrument_data['arr_close'][-1] <= instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_close'][-2] >= instrument_data['arr_LongTermMA'][-2]
                    
                    
                # Calculate the ADXR using talib.ADXR
                adxr = talib.ADXR(instrument_data['highprice'], instrument_data['lowprice'], instrument_data['arr_close'], timeperiod=self.general_period)
                    
                # Caclulate the APO for momentum detection
                apo = talib.APO(instrument_data['arr_close'], self.midperiod, self.slowperiod)
                    
                macd, signal, hist = talib.MACD(instrument_data['arr_close'], self.fastperiod, self.slowperiod, self.midperiod)
                    
                # Calculate Aroon values
                aroon_up, aroon_down = talib.AROON(instrument_data['highprice'], instrument_data['lowprice'], timeperiod=self.general_period)
                aroonosc = aroon_up - aroon_down
                    
                ranging = self.rangingFilter(adxr[-1], aroonosc[-1])
                bullish = self.momentumFilter(apo[-1], macd, aroonosc, price_above_longtermMA, LongTermEMA_rising)
                    
                    
                    
                if not numpy.isnan(instrument_data['arr_fastMA'][-1]) and not numpy.isnan(instrument_data['arr_fastMA'][-2]) and not numpy.isnan(instrument_data['arr_slowMA'][-1]) and not numpy.isnan(instrument_data['arr_slowMA'][-2]) and not numpy.isnan(instrument_data['arr_midMA'][-1]) and not numpy.isnan(instrument_data['arr_midMA'][-2]):
                    # send a buy order for Golden Cross (fastMA above slowMA, midMA crosses above slowMA)
                    if (not ranging and bullish == 1) and ((instrument_data['arr_fastMA'][-1] > instrument_data['arr_slowMA'][-1] and instrument_data['arr_midMA'][-1] > instrument_data['arr_slowMA'][-1] and instrument_data['arr_midMA'][-2] < instrument_data['arr_slowMA'][-2]) or price_cross_above_longtermMA):
                        instrument_data['entry_signal'] = 1
                        
                    # send a sell order for Death Cross
                    elif (not ranging and bullish == -1) and ((instrument_data['arr_fastMA'][-1] < instrument_data['arr_slowMA'][-1] and instrument_data['arr_midMA'][-1] < instrument_data['arr_slowMA'][-1] and instrument_data['arr_midMA'][-2] > instrument_data['arr_slowMA'][-2]) or price_cross_below_longtermMA):
                        instrument_data['entry_signal'] = -1
                        
                    else:
                        instrument_data['entry_signal'] = 0
                        
                else:
                    instrument_data['entry_signal'] = 0
            
                # update stoploss point dynamically
                if self.openOrder:
                    self.update_stoploss(instrument, instrument_data['stoploss'])
            
            count = 0
            # checking all instruments for entry signals and find total number of entry signals
            for instrument in bd:
                if self.instrument_data[instrument]['entry_signal'] == 1 or self.instrument_data[instrument]['entry_signal'] == -1:
                    count += 1
                
            availableBalance = ab['availableBalance']
            for instrument in bd: 
                if self.instrument_data[instrument]['entry_signal'] == 1 or self.instrument_data[instrument]['entry_signal'] == -1:
                    lastprice = bd[instrument]['lastPrice']
                    volume = self.find_positionSize(lastprice, 1/count * 1/self.no_instrument * availableBalance * 2)
                    direction = self.instrument_data[instrument]['entry_signal']
                    stoploss = self.instrument_data[instrument]['stoploss']
                    self.test_sendOrder(lastprice, direction, 'open', volume, stoploss, instrument)
               

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
    
    def test_sendOrder(self, lastprice, buysell, openclose, volume, stoploss, instrument):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = instrument
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
                openclose = 'close'
            )
            self.evt.sendOrder(order)
        return True
    
    # ATR trailing stop implementation
    def update_stoploss(self, instrument, new_stoploss):
        for ID in self.openOrder:
            openPosition = self.openOrder[ID]
            if openPosition['instrument'] == instrument:
                if openPosition['buysell'] == 1 and openPosition['stopLossLevel'] < openPosition['openprice'] - new_stoploss: 
                    # for buy ordder, update stop loss if current ATR stop is higher than previous 
                    res = self.evt.update_opened_order(tradeID=ID, sl = openPosition['openprice'] - new_stoploss)
                    # update the update stop loss using ATR stop
                elif openPosition['buysell'] == -1 and openPosition['openprice'] + new_stoploss < openPosition['stopLossLevel']: 
                    # for buy ordder, update stop loss if current ATR stop is higher than previous 
                    res = self.evt.update_opened_order(tradeID=ID, sl = openPosition['openprice'] + new_stoploss)
                    # update the update stop loss using ATR stop
        
    # utility function to find volume based on available balance
    def find_positionSize(self, lastprice, allowance):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        ratio = 0.9
        volume = (allowance*ratio) / lastprice
        total =  volume * lastprice
        while total < 0.9 * allowance:
            ratio *= 1.05
            volume = (allowance*ratio) / lastprice
            total =  volume * lastprice
        while total > 0.9 * allowance or total > availableBalance:
            ratio *= 0.95
            volume = (allowance*ratio) / lastprice
            total =  volume * lastprice
        return volume
    
